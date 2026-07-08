"use client";

import { useEffect, useState, type FormEvent } from "react";

import { Alert } from "@/components/ui/Alert";
import { approvalStatusTone, Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { ApiError } from "@/lib/api/client";
import * as driverApi from "@/lib/api/driver";
import { VEHICLE_CATEGORY_ICONS, VEHICLE_CATEGORY_LABELS } from "@/lib/format";
import type { DriverProfile, Vehicle, VehicleCategory } from "@/types/api";

type Message = { tone: "success" | "error"; text: string } | null;

const CATEGORIES: VehicleCategory[] = ["KEKE", "CAR"];

export default function OnboardingPage() {
  const [profile, setProfile] = useState<DriverProfile | null>(null);
  const [license, setLicense] = useState("");
  const [profileBusy, setProfileBusy] = useState(false);
  const [profileMsg, setProfileMsg] = useState<Message>(null);

  const [vehicle, setVehicle] = useState({
    make: "",
    model: "",
    year: "",
    color: "",
    plate_number: "",
  });
  const [category, setCategory] = useState<VehicleCategory>("CAR");
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [vehicleErrors, setVehicleErrors] = useState<Record<string, string[]>>({});
  const [vehicleBusy, setVehicleBusy] = useState(false);
  const [vehicleMsg, setVehicleMsg] = useState<Message>(null);

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [p, v] = await Promise.all([driverApi.getProfile(), driverApi.getVehicle()]);
        if (cancelled) return;
        setProfile(p);
        setLicense(p.license_number);
        // Vehicle category is fixed by the driver's registered category in V1
        setCategory(p.driver_category);
        if (v) {
          setVehicle({
            make: v.make,
            model: v.model,
            year: String(v.year),
            color: v.color,
            plate_number: v.plate_number,
          });
          setPhotoPreview(v.photo_url);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  function onPhotoChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setPhotoFile(file);
    if (file) setPhotoPreview(URL.createObjectURL(file));
  }

  const setV = (key: keyof typeof vehicle) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setVehicle((prev) => ({ ...prev, [key]: e.target.value }));

  async function saveProfile(e: FormEvent) {
    e.preventDefault();
    setProfileBusy(true);
    setProfileMsg(null);
    try {
      const updated = await driverApi.updateProfile({ license_number: license });
      setProfile(updated);
      setProfileMsg({ tone: "success", text: "License details saved." });
    } catch (err) {
      setProfileMsg({
        tone: "error",
        text: err instanceof ApiError ? err.message : "Could not save. Try again.",
      });
    } finally {
      setProfileBusy(false);
    }
  }

  async function saveVehicle(e: FormEvent) {
    e.preventDefault();
    setVehicleBusy(true);
    setVehicleMsg(null);
    setVehicleErrors({});
    try {
      const saved = await driverApi.saveVehicle({ ...vehicle, category, photo: photoFile });
      setPhotoFile(null);
      setPhotoPreview(saved.photo_url);
      setVehicleMsg({ tone: "success", text: "Vehicle saved." });
    } catch (err) {
      if (err instanceof ApiError) {
        setVehicleErrors(err.fieldErrors);
        if (!Object.keys(err.fieldErrors).length) {
          setVehicleMsg({ tone: "error", text: err.message });
        }
      } else {
        setVehicleMsg({ tone: "error", text: "Could not save. Try again." });
      }
    } finally {
      setVehicleBusy(false);
    }
  }

  if (loading || !profile) return <FullPageSpinner />;

  const fieldError = (key: string) => vehicleErrors[key]?.join(" ");

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-gray-900">Driver profile</h2>
        <Badge tone={approvalStatusTone(profile.approval_status)}>{profile.approval_status}</Badge>
      </div>

      {profile.approval_status === "REJECTED" && profile.approval_note && (
        <Alert tone="error">Rejection reason: {profile.approval_note}</Alert>
      )}

      <Card>
        <form onSubmit={saveProfile} className="space-y-4">
          <h3 className="font-semibold text-gray-900">License</h3>
          {profileMsg && <Alert tone={profileMsg.tone}>{profileMsg.text}</Alert>}
          <Input
            label="Driver's license number"
            value={license}
            onChange={(e) => setLicense(e.target.value)}
            hint={
              profile.approval_status === "APPROVED"
                ? "Changing your license number sends your account back for re-approval."
                : undefined
            }
            required
          />
          <Button type="submit" fullWidth loading={profileBusy}>
            Save license details
          </Button>
        </form>
      </Card>

      <Card>
        <form onSubmit={saveVehicle} className="space-y-4">
          <h3 className="font-semibold text-gray-900">Vehicle</h3>
          {vehicleMsg && <Alert tone={vehicleMsg.tone}>{vehicleMsg.text}</Alert>}
          <div>
            <p className="mb-2 text-sm font-medium text-gray-700">Vehicle type</p>
            <div className="grid grid-cols-2 gap-2">
              {CATEGORIES.map((c) => {
                const locked = !!profile && c !== profile.driver_category;
                return (
                  <button
                    key={c}
                    type="button"
                    disabled={locked}
                    onClick={() => !locked && setCategory(c)}
                    className={`rounded-lg border px-3 py-3 text-sm font-semibold ${
                      category === c
                        ? "border-emerald-600 bg-emerald-50 text-emerald-700"
                        : locked
                          ? "border-gray-200 bg-gray-100 text-gray-400"
                          : "border-gray-300 bg-white text-gray-700"
                    }`}
                  >
                    <span className="mr-1 text-lg" aria-hidden>
                      {VEHICLE_CATEGORY_ICONS[c]}
                    </span>
                    {VEHICLE_CATEGORY_LABELS[c]}
                  </button>
                );
              })}
            </div>
            {profile && (
              <p className="mt-1 text-xs text-gray-500">
                You registered as a {VEHICLE_CATEGORY_LABELS[profile.driver_category]} driver.
                To operate a different vehicle type, contact support.
              </p>
            )}
            {vehicleErrors.category && (
              <p className="mt-1 text-xs text-red-600">{vehicleErrors.category.join(" ")}</p>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Make" placeholder="Toyota" value={vehicle.make} onChange={setV("make")} error={fieldError("make")} required />
            <Input label="Model" placeholder="Corolla" value={vehicle.model} onChange={setV("model")} error={fieldError("model")} required />
            <Input label="Year" type="number" placeholder="2016" value={vehicle.year} onChange={setV("year")} error={fieldError("year")} required />
            <Input label="Color" placeholder="Black" value={vehicle.color} onChange={setV("color")} error={fieldError("color")} required />
          </div>
          <Input
            label="Plate number"
            placeholder="ABC123XY"
            value={vehicle.plate_number}
            onChange={setV("plate_number")}
            error={fieldError("plate_number")}
            required
          />
          <div className="space-y-2">
            <label htmlFor="vehicle-photo" className="block text-sm font-medium text-gray-700">
              Vehicle photo{photoPreview ? "" : " (recommended)"}
            </label>
            {photoPreview && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={photoPreview}
                alt="Vehicle"
                className="h-36 w-full rounded-lg border border-gray-200 object-cover"
              />
            )}
            <input
              id="vehicle-photo"
              type="file"
              accept="image/*"
              onChange={onPhotoChange}
              className="block w-full text-sm text-gray-600 file:mr-3 file:rounded-lg file:border-0 file:bg-emerald-50 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-emerald-700"
            />
            {vehicleErrors.photo && (
              <p className="text-xs text-red-600">{vehicleErrors.photo.join(" ")}</p>
            )}
            <p className="text-xs text-gray-500">
              Passengers see this photo when you accept their ride.
            </p>
          </div>
          <Button type="submit" fullWidth loading={vehicleBusy}>
            Save vehicle
          </Button>
        </form>
      </Card>
    </div>
  );
}
