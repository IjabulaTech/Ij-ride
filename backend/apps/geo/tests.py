from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.services import register_passenger

from .base import AddressNotFoundError, GeoServiceError
from .providers.google import GoogleGeoProvider
from .providers.mapbox import MapboxGeoProvider
from .providers.osm import OsmGeoProvider
from .providers.stub import StubGeoProvider
from .service import _provider_for, get_geo_provider
from .utils import haversine_m

PASSWORD = "str0ng-Pass-2026"


class HaversineTests(SimpleTestCase):
    def test_known_distance(self):
        # American University of Nigeria (9.3345, 12.4944) to Modibbo Adama
        # University (9.2028, 12.4810) in Yola is ~14.7 km straight-line.
        distance = haversine_m(9.3345, 12.4944, 9.2028, 12.4810)
        self.assertTrue(14_000 < distance < 15_500, distance)

    def test_zero_distance(self):
        self.assertEqual(haversine_m(9.2035, 12.4954, 9.2035, 12.4954), 0)


class StubProviderTests(SimpleTestCase):
    def setUp(self):
        self.provider = StubGeoProvider()

    def test_geocode_is_deterministic_and_near_yola_center(self):
        a = self.provider.geocode("Jimeta Modern Market")
        b = self.provider.geocode("jimeta modern market")  # case-insensitive same point
        self.assertEqual((a.lat, a.lng), (b.lat, b.lng))
        # Yola sits at ~9.20 N, 12.50 E; stub spread is ~±0.09 around it
        self.assertTrue(Decimal("9.05") < a.lat < Decimal("9.35"), a.lat)
        self.assertTrue(Decimal("12.35") < a.lng < Decimal("12.65"), a.lng)

    def test_route_applies_road_factor_and_speed(self):
        route = self.provider.route(
            (Decimal("9.3345"), Decimal("12.4944")),
            (Decimal("9.2028"), Decimal("12.4810")),
        )
        straight = haversine_m("9.3345", "12.4944", "9.2028", "12.4810")
        self.assertEqual(route.distance_m, round(straight * 1.4))
        self.assertGreater(route.duration_s, 0)

    def test_suggest_returns_yola_gazetteer_hits(self):
        results = self.provider.suggest("Jimeta", limit=5)
        self.assertGreater(len(results), 0)
        self.assertTrue(all("Adamawa" in s.address for s in results))
        # Case-insensitive
        self.assertEqual(len(self.provider.suggest("jimeta")), len(results))

    def test_suggest_resolves_local_acronyms(self):
        for query, expected_label in (
            ("AUN", "American University"),
            ("aun", "American University"),
            ("FMC", "Federal Medical Centre"),
            ("MAU", "Modibbo Adama"),
        ):
            results = self.provider.suggest(query, limit=3)
            self.assertTrue(results, f"no results for {query!r}")
            self.assertIn(expected_label, results[0].label)
            self.assertTrue(results[0].place_type)  # populated
            self.assertTrue(results[0].place_name)

    def test_suggest_falls_back_deterministically(self):
        # Not in the gazetteer -> stub returns a Yola-labeled fallback
        results = self.provider.suggest("completely-made-up-place-xyz")
        self.assertEqual(len(results), 1)
        self.assertIn("Yola, Adamawa", results[0].address)

    def test_suggest_empty_query(self):
        self.assertEqual(self.provider.suggest(""), [])

    def test_reverse_geocode_near_known_place(self):
        # AUN is in the gazetteer; a pin near it should be labelled "Near …"
        result = self.provider.reverse_geocode(Decimal("9.3350"), Decimal("12.4948"))
        self.assertIn("American University of Nigeria", result.address)
        self.assertEqual(result.lat, Decimal("9.3350"))

    def test_reverse_geocode_far_from_gazetteer(self):
        result = self.provider.reverse_geocode(Decimal("9.4000"), Decimal("13.0000"))
        self.assertIn("Pinned location", result.address)


class ProviderSelectionTests(SimpleTestCase):
    def tearDown(self):
        _provider_for.cache_clear()

    @override_settings(GEO_PROVIDER="stub")
    def test_stub_selected(self):
        self.assertIsInstance(get_geo_provider(), StubGeoProvider)

    @override_settings(GEO_PROVIDER="nonsense")
    def test_unknown_provider_raises(self):
        with self.assertRaises(ValueError):
            get_geo_provider()


@override_settings(MAPBOX_ACCESS_TOKEN="test-token", GEO_COUNTRY="NG", GEO_PROXIMITY="12.4954,9.2035")
class MapboxProviderTests(SimpleTestCase):
    def _response(self, payload, status=200):
        resp = mock.Mock()
        resp.status_code = status
        resp.json.return_value = payload
        return resp

    def test_geocode_parses_feature(self):
        provider = MapboxGeoProvider()
        payload = {
            "features": [
                {
                    "geometry": {"coordinates": [12.494400, 9.334500]},
                    "properties": {"name": "Yola", "full_address": "Yola, Adamawa, Nigeria"},
                }
            ]
        }
        with mock.patch.object(provider.session, "get", return_value=self._response(payload)) as m:
            result = provider.geocode("Yola")
        self.assertEqual(result.address, "Yola, Adamawa, Nigeria")
        self.assertEqual(result.lat, Decimal("9.334500"))
        self.assertEqual(result.lng, Decimal("12.494400"))
        params = m.call_args.kwargs["params"]
        self.assertEqual(params["country"], "ng")
        self.assertEqual(params["q"], "Yola")
        self.assertEqual(params["bbox"], "11.3,7.4,13.7,11.4")

    def test_geocode_no_results_raises_not_found(self):
        provider = MapboxGeoProvider()
        with mock.patch.object(provider.session, "get", return_value=self._response({"features": []})):
            with self.assertRaises(AddressNotFoundError):
                provider.geocode("zzzz nowhere")

    def test_route_parses_distance_and_duration(self):
        provider = MapboxGeoProvider()
        payload = {"code": "Ok", "routes": [{"distance": 10412.7, "duration": 1503.2}]}
        with mock.patch.object(provider.session, "get", return_value=self._response(payload)):
            route = provider.route(
                (Decimal("9.3345"), Decimal("12.4944")),
                (Decimal("9.2028"), Decimal("12.4810")),
            )
        self.assertEqual(route.distance_m, 10413)
        self.assertEqual(route.duration_s, 1503)

    def test_provider_error_on_http_failure(self):
        provider = MapboxGeoProvider()
        with mock.patch.object(provider.session, "get", return_value=self._response({}, status=500)):
            with self.assertRaises(GeoServiceError):
                provider.route(
                    (Decimal("9.3345"), Decimal("12.4944")),
                    (Decimal("9.2028"), Decimal("12.4810")),
                )

    def test_suggest_uses_searchbox_bbox_types_language(self):
        provider = MapboxGeoProvider()
        # "Zerofoo" won't match the local POI dict so we exercise the Mapbox
        # Search Box call path directly
        payload = {
            "features": [
                {
                    "geometry": {"coordinates": [12.4473, 9.2611]},
                    "properties": {
                        "name": "Zerofoo Store",
                        "full_address": "Zerofoo Store, Yola North, Adamawa, Nigeria",
                        "feature_type": "poi",
                        "poi_category": ["shopping"],
                    },
                },
            ]
        }
        with mock.patch.object(provider.session, "get", return_value=self._response(payload)) as m:
            results = provider.suggest("Zerofoo", limit=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].label, "Zerofoo Store")
        self.assertEqual(results[0].place_type, "shopping")
        params = m.call_args.kwargs["params"]
        self.assertEqual(params["q"], "Zerofoo")
        self.assertEqual(params["country"], "ng")
        self.assertEqual(params["proximity"], "12.4954,9.2035")
        self.assertEqual(params["bbox"], "11.3,7.4,13.7,11.4")
        self.assertIn("poi", params["types"])
        self.assertEqual(params["language"], "en")

    def test_suggest_prefers_local_poi_over_mapbox(self):
        provider = MapboxGeoProvider()
        payload = {
            "features": [
                {
                    "geometry": {"coordinates": [3.3792, 6.5244]},
                    "properties": {
                        "name": "Lagos Aunty Cafe",
                        "full_address": "Lagos Aunty Cafe, Lagos, Nigeria",
                        "feature_type": "poi",
                    },
                },
            ]
        }
        with mock.patch.object(provider.session, "get", return_value=self._response(payload)):
            results = provider.suggest("AUN", limit=5)
        # Local Yola POI must beat Mapbox's Lagos hit at the top
        self.assertEqual(results[0].label, "American University of Nigeria")
        self.assertNotIn("Lagos", results[0].address)

    def test_suggest_uses_live_gps_as_proximity(self):
        provider = MapboxGeoProvider()
        with mock.patch.object(
            provider.session, "get", return_value=self._response({"features": []})
        ) as m:
            provider.suggest("Zerofoo", limit=5, proximity=(Decimal("9.334500"), Decimal("12.494400")))
        params = m.call_args.kwargs["params"]
        # Mapbox expects "lng,lat"
        self.assertEqual(params["proximity"], "12.494400,9.334500")

    def test_suggest_swallows_provider_errors(self):
        provider = MapboxGeoProvider()
        with mock.patch.object(provider.session, "get", return_value=self._response({}, status=500)):
            self.assertEqual(provider.suggest("anything"), [])

    def test_reverse_geocode_parses_place(self):
        provider = MapboxGeoProvider()
        payload = {
            "features": [
                {
                    "geometry": {"coordinates": [12.4948, 9.3350]},
                    "properties": {"name": "AUN", "full_address": "AUN, Yola, Adamawa, Nigeria"},
                }
            ]
        }
        with mock.patch.object(provider.session, "get", return_value=self._response(payload)):
            result = provider.reverse_geocode(Decimal("9.3350"), Decimal("12.4948"))
        self.assertIn("AUN", result.address)

    def test_reverse_geocode_gracefully_falls_back(self):
        provider = MapboxGeoProvider()
        with mock.patch.object(provider.session, "get", return_value=self._response({}, status=500)):
            result = provider.reverse_geocode(Decimal("9.20"), Decimal("12.50"))
        self.assertIn("Pinned location", result.address)


@override_settings(
    GEO_OSM_BASE_URL="https://photon.test",
    GEO_COUNTRY="NG",
    GEO_PROXIMITY="12.4954,9.2035",
)
class OsmProviderTests(SimpleTestCase):
    def _response(self, payload, status=200):
        resp = mock.Mock()
        resp.status_code = status
        resp.json.return_value = payload
        return resp

    @staticmethod
    def _feature(name, lng, lat, *, cc="NG", state="Adamawa", value="hotel", city="Yola"):
        return {
            "geometry": {"coordinates": [lng, lat]},
            "properties": {
                "name": name,
                "osm_value": value,
                "city": city,
                "state": state,
                "countrycode": cc,
            },
        }

    def test_suggest_filters_to_adamawa_and_parses(self):
        provider = OsmGeoProvider()
        payload = {
            "features": [
                self._feature("Madugu Rockview Hotel", 12.45, 9.19),
                # Border town the bbox clips in — different country, must drop
                self._feature("Hotel Ribadou", 13.4, 9.3, cc="CM", state="North", city="Garoua"),
            ]
        }
        with mock.patch.object(provider.session, "get", return_value=self._response(payload)) as m:
            results = provider.suggest("Rockview", limit=6)
        labels = [r.label for r in results]
        self.assertIn("Madugu Rockview Hotel", labels)
        self.assertNotIn("Hotel Ribadou", labels)  # Cameroon filtered out
        self.assertEqual(results[0].place_type, "hotel")
        self.assertIn("Adamawa", results[0].address)
        params = m.call_args.kwargs["params"]
        self.assertEqual(params["q"], "Rockview")
        self.assertEqual(params["bbox"], "11.3,7.4,13.7,11.4")
        self.assertEqual(params["lat"], "9.2035")
        self.assertEqual(params["lon"], "12.4954")

    def test_suggest_prefers_local_poi(self):
        provider = OsmGeoProvider()
        payload = {"features": [self._feature("Somewhere Else", 12.4, 9.2)]}
        with mock.patch.object(provider.session, "get", return_value=self._response(payload)):
            results = provider.suggest("AUN", limit=5)
        self.assertEqual(results[0].label, "American University of Nigeria")

    def test_geocode_returns_first_adamawa_hit(self):
        provider = OsmGeoProvider()
        payload = {
            "features": [
                self._feature("Elsewhere", 3.3, 6.5, cc="NG", state="Lagos"),  # filtered
                self._feature("Jimeta Modern Market", 12.46, 9.28, value="marketplace"),
            ]
        }
        with mock.patch.object(provider.session, "get", return_value=self._response(payload)):
            result = provider.geocode("Jimeta Modern Market")
        self.assertIn("Jimeta Modern Market", result.address)
        self.assertEqual(result.lat, Decimal("9.280000"))

    def test_geocode_no_results_raises(self):
        provider = OsmGeoProvider()
        with mock.patch.object(provider.session, "get", return_value=self._response({"features": []})):
            with self.assertRaises(AddressNotFoundError):
                provider.geocode("nowhere at all")

    def test_reverse_geocode_parses(self):
        provider = OsmGeoProvider()
        payload = {"features": [self._feature("AUN", 12.4948, 9.3350, value="university")]}
        with mock.patch.object(provider.session, "get", return_value=self._response(payload)):
            result = provider.reverse_geocode(Decimal("9.3350"), Decimal("12.4948"))
        self.assertIn("AUN", result.address)
        self.assertEqual(result.lat, Decimal("9.3350"))

    def test_suggest_swallows_provider_errors(self):
        provider = OsmGeoProvider()
        with mock.patch.object(provider.session, "get", return_value=self._response({}, status=500)):
            # Non-local query + provider error -> empty, no raise
            self.assertEqual(provider.suggest("Zerofoo-nowhere"), [])

    @override_settings(MAPBOX_ACCESS_TOKEN="")
    def test_route_falls_back_to_haversine_without_token(self):
        provider = OsmGeoProvider()
        route = provider.route(
            (Decimal("9.3345"), Decimal("12.4944")), (Decimal("9.2028"), Decimal("12.4810"))
        )
        straight = haversine_m("9.3345", "12.4944", "9.2028", "12.4810")
        self.assertEqual(route.distance_m, round(straight * 1.4))
        self.assertGreater(route.duration_s, 0)


@override_settings(GOOGLE_MAPS_API_KEY="test-google-key", MAPBOX_ACCESS_TOKEN="")
class GoogleProviderTests(SimpleTestCase):
    def _response(self, payload, status=200):
        resp = mock.Mock()
        resp.status_code = status
        resp.json.return_value = payload
        return resp

    @staticmethod
    def _place(name, lat, lng, *, ptype="lodging", addr=None):
        return {
            "displayName": {"text": name},
            "formattedAddress": addr or f"{name}, Yola, Adamawa, Nigeria",
            "location": {"latitude": lat, "longitude": lng},
            "primaryType": ptype,
            "types": [ptype],
        }

    def test_suggest_parses_places_and_restricts_to_adamawa(self):
        provider = GoogleGeoProvider()
        payload = {"places": [self._place("Grand Peace Hotel", 9.26, 12.47)]}
        with mock.patch.object(provider.session, "post", return_value=self._response(payload)) as m:
            results = provider.suggest("Grand Peace Hotel", limit=6)
        self.assertEqual(results[0].label, "Grand Peace Hotel")
        self.assertEqual(results[0].place_type, "lodging")
        self.assertEqual(results[0].lat, Decimal("9.260000"))
        body = m.call_args.kwargs["json"]
        self.assertEqual(body["textQuery"], "Grand Peace Hotel")
        self.assertEqual(body["regionCode"], "NG")
        self.assertIn("locationRestriction", body)
        self.assertEqual(body["locationRestriction"]["rectangle"]["low"]["latitude"], 7.4)
        headers = m.call_args.kwargs["headers"]
        self.assertEqual(headers["X-Goog-Api-Key"], "test-google-key")
        self.assertIn("places.location", headers["X-Goog-FieldMask"])

    def test_suggest_prefers_local_poi(self):
        provider = GoogleGeoProvider()
        payload = {"places": [self._place("Somewhere", 9.2, 12.4)]}
        with mock.patch.object(provider.session, "post", return_value=self._response(payload)):
            results = provider.suggest("AUN", limit=5)
        self.assertEqual(results[0].label, "American University of Nigeria")

    def test_geocode_returns_first_place(self):
        provider = GoogleGeoProvider()
        payload = {"places": [self._place("Jimeta Modern Market", 9.261, 12.447, ptype="market")]}
        with mock.patch.object(provider.session, "post", return_value=self._response(payload)):
            result = provider.geocode("Jimeta Modern Market")
        self.assertIn("Jimeta Modern Market", result.address)
        self.assertEqual(result.lat, Decimal("9.261000"))

    def test_geocode_no_results_raises(self):
        provider = GoogleGeoProvider()
        with mock.patch.object(provider.session, "post", return_value=self._response({"places": []})):
            with self.assertRaises(AddressNotFoundError):
                provider.geocode("nowhere at all xyz")

    def test_reverse_geocode_parses(self):
        provider = GoogleGeoProvider()
        payload = {"results": [{"formatted_address": "AUN, Yola, Adamawa, Nigeria"}]}
        with mock.patch.object(provider.session, "get", return_value=self._response(payload)):
            result = provider.reverse_geocode(Decimal("9.3350"), Decimal("12.4948"))
        self.assertIn("AUN", result.address)
        self.assertEqual(result.lat, Decimal("9.3350"))

    def test_suggest_swallows_errors(self):
        provider = GoogleGeoProvider()
        with mock.patch.object(provider.session, "post", return_value=self._response({}, status=500)):
            self.assertEqual(provider.suggest("Zerofoo-nowhere"), [])

    @override_settings(GOOGLE_MAPS_API_KEY="")
    def test_missing_key_degrades_gracefully(self):
        provider = GoogleGeoProvider()
        # No key: non-local query yields nothing rather than raising / 500ing
        self.assertEqual(provider.suggest("Zerofoo-nowhere"), [])
        r = provider.reverse_geocode(Decimal("9.2"), Decimal("12.5"))
        self.assertIn("Pinned location", r.address)

    def test_route_uses_haversine_without_mapbox_token(self):
        provider = GoogleGeoProvider()
        route = provider.route(
            (Decimal("9.3345"), Decimal("12.4944")), (Decimal("9.2028"), Decimal("12.4810"))
        )
        straight = haversine_m("9.3345", "12.4944", "9.2028", "12.4810")
        self.assertEqual(route.distance_m, round(straight * 1.4))


class GeoApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = register_passenger(phone="+2348031900001", password=PASSWORD)
        self.client.force_authenticate(user=self.user)

    def test_suggest_requires_auth(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get(reverse("geo:suggest"), {"q": "Jimeta"})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_suggest_returns_results_for_yola_query(self):
        resp = self.client.get(reverse("geo:suggest"), {"q": "Jimeta"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        results = resp.data["results"]
        self.assertGreater(len(results), 0)
        for row in results:
            self.assertIn("Adamawa", row["address"])
            self.assertIn("lat", row)
            self.assertIn("lng", row)
            self.assertIn("place_name", row)
            self.assertIn("place_type", row)

    def test_suggest_partial_gps_pair_rejected(self):
        resp = self.client.get(reverse("geo:suggest"), {"q": "Jimeta", "lat": "9.2"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_suggest_requires_query_param(self):
        resp = self.client.get(reverse("geo:suggest"))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reverse_endpoint(self):
        resp = self.client.get(
            reverse("geo:reverse"), {"lat": "9.3350", "lng": "12.4948"}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertIn("address", resp.data)
        self.assertEqual(resp.data["lat"], "9.335000")


class EstimateCoordinatePreservationTests(APITestCase):
    """Coordinates from 'Use current location' must flow through unchanged
    into the fare calculation — not silently replaced by geocoded points."""

    def setUp(self):
        cache.clear()
        from apps.pricing.models import FareSetting

        FareSetting.objects.create(
            vehicle_category="CAR",
            base_fare=Decimal("500"),
            per_km=Decimal("120"),
            per_minute=Decimal("15"),
            minimum_fare=Decimal("700"),
            rounding_step=Decimal("50"),
            is_active=True,
        )
        self.user = register_passenger(phone="+2348031900002", password=PASSWORD)
        self.client.force_authenticate(user=self.user)

    def test_supplied_coordinates_are_used_verbatim(self):
        pickup_lat, pickup_lng = "9.334500", "12.494400"
        dropoff_lat, dropoff_lng = "9.202800", "12.481000"
        resp = self.client.post(
            reverse("rides:estimate"),
            {
                "vehicle_category": "CAR",
                "pickup": {"address": "Current location", "lat": pickup_lat, "lng": pickup_lng},
                "dropoff": {"address": "Modibbo Adama University", "lat": dropoff_lat, "lng": dropoff_lng},
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        # Backend must echo exactly the coords we sent (no stub re-geocode)
        self.assertEqual(resp.data["pickup"]["lat"], pickup_lat)
        self.assertEqual(resp.data["pickup"]["lng"], pickup_lng)
        self.assertEqual(resp.data["dropoff"]["lat"], dropoff_lat)
        self.assertEqual(resp.data["dropoff"]["lng"], dropoff_lng)
        # Distance derived from those exact coords (~14.7 km straight-line -> ~20.6 km road)
        self.assertGreater(resp.data["distance_m"], 18_000)
        self.assertLess(resp.data["distance_m"], 23_000)
