import type { Metadata } from "next";
import Link from "next/link";

import { BrandLogo } from "@/components/ui/BrandLogo";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "How IJ Ride collects, uses, and protects your personal information.",
};

const EFFECTIVE_DATE = "12 October 2026";
const SUPPORT_PHONE = "09067274895";
const SUPPORT_EMAIL = "support@ijrides.com";

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="space-y-3">
      <h2 className="text-lg font-bold text-gray-900">{title}</h2>
      <div className="space-y-3 text-sm leading-relaxed text-gray-700">{children}</div>
    </section>
  );
}

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
          <Link href="/" className="flex items-center gap-2">
            <BrandLogo size={30} />
            <span className="text-lg font-bold text-gray-900">IJ Ride</span>
          </Link>
          <Link href="/login" className="text-sm font-semibold text-blue-600 hover:underline">
            Open app
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl space-y-8 px-4 py-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-extrabold text-gray-900">Privacy Policy</h1>
          <p className="text-sm text-gray-500">Last updated: {EFFECTIVE_DATE}</p>
        </div>

        <p className="text-sm leading-relaxed text-gray-700">
          This Privacy Policy explains how <strong>IJ Ride</strong> (&ldquo;IJ Ride&rdquo;,
          &ldquo;we&rdquo;, &ldquo;us&rdquo;), a ride-hailing service operating in Yola, Adamawa
          State, Nigeria, collects, uses, shares, and protects your personal information when you
          use our mobile application and website at ijrides.com (together, the &ldquo;Service&rdquo;).
          By using the Service, you agree to this Policy. If you do not agree, please do not use the
          Service.
        </p>

        <Section id="who-we-are" title="1. Who we are">
          <p>
            IJ Ride connects passengers with KEKE (tricycle) and car drivers for trips within
            Adamawa State. We act as the data controller for the personal information described
            here. You can reach us using the details in the &ldquo;Contact us&rdquo; section below.
          </p>
        </Section>

        <Section id="information-we-collect" title="2. Information we collect">
          <p>We collect the following information, depending on how you use the Service:</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>
              <strong>Account details:</strong> your name, phone number, password (stored
              encrypted), and email address (optional).
            </li>
            <li>
              <strong>Identity verification:</strong> your National Identification Number (NIN),
              where you choose to provide it, so we can verify your identity for safety and trust.
            </li>
            <li>
              <strong>Driver details (drivers only):</strong> driver&rsquo;s licence number, vehicle
              make, model, year, colour and plate number, and photographs of you and your vehicle.
            </li>
            <li>
              <strong>Location information:</strong> your GPS location while you use the Service — to
              set pickup and drop-off points, match you with nearby drivers, and show live trip
              tracking, estimated time of arrival and distance.
            </li>
            <li>
              <strong>Trip and payment information:</strong> pickup and drop-off addresses, trip
              history, fares, and your chosen payment method (cash or bank transfer). We do{" "}
              <strong>not</strong> collect or store your bank card or account numbers.
            </li>
            <li>
              <strong>Communications:</strong> messages you send to our in-app support chat.
            </li>
            <li>
              <strong>Device and usage data:</strong> basic technical information such as device
              type, app version, and log data needed to operate and secure the Service.
            </li>
          </ul>
        </Section>

        <Section id="how-we-use" title="3. How we use your information">
          <ul className="list-disc space-y-1 pl-5">
            <li>To create and manage your account and let you log in.</li>
            <li>To request, match, price, track, and complete rides.</li>
            <li>To verify drivers and users and keep the community safe.</li>
            <li>To process the record of payments agreed between passengers and drivers.</li>
            <li>To provide customer support and respond to your messages.</li>
            <li>To send one-time codes (for example, to reset your password) by SMS.</li>
            <li>To maintain, secure, troubleshoot, and improve the Service.</li>
            <li>To comply with legal obligations and enforce our terms.</li>
          </ul>
        </Section>

        <Section id="location" title="4. Location information">
          <p>
            Location is central to a ride-hailing service. While you are using the app to book,
            drive, or track a trip, we use your device&rsquo;s location to match passengers and
            drivers and to show the live route and ETA. Drivers&rsquo; approximate location is shared
            with the matched passenger during an active trip, and vice versa, so you can find each
            other.
          </p>
          <p>
            You can turn off location access at any time in your device settings, but core features
            such as booking a ride or receiving ride requests will not work without it.
          </p>
        </Section>

        <Section id="how-we-share" title="5. How we share your information">
          <p>We do not sell your personal information. We share it only as follows:</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>
              <strong>Between passengers and drivers:</strong> when a ride is matched, we share the
              limited details needed to complete the trip — for example, name, phone number, photo,
              vehicle details, and live location during the trip.
            </li>
            <li>
              <strong>Service providers</strong> who help us run the Service, under agreements that
              require them to protect your data: maps and place search (Google Maps Platform,
              Mapbox, OpenStreetMap), image hosting (Cloudinary), application and database hosting
              (Render, Vercel, Neon), and SMS delivery (Termii). These providers may process data
              outside Nigeria; where they do, we rely on appropriate safeguards.
            </li>
            <li>
              <strong>Legal and safety:</strong> where required by law, legal process, or to protect
              the rights, safety, and property of users, the public, or IJ Ride.
            </li>
          </ul>
        </Section>

        <Section id="retention" title="6. How long we keep your information">
          <p>
            We keep your information for as long as your account is active and as needed to provide
            the Service, resolve disputes, meet legal and tax obligations, and enforce our
            agreements. When information is no longer needed, we delete or anonymise it.
          </p>
        </Section>

        <Section id="security" title="7. How we protect your information">
          <p>
            We use reasonable technical and organisational measures to protect your information,
            including encrypted connections (HTTPS), hashed passwords, and access controls. No method
            of transmission or storage is completely secure, so we cannot guarantee absolute
            security, but we work to protect your data and continually improve our safeguards.
          </p>
        </Section>

        <Section id="your-rights" title="8. Your rights">
          <p>
            Subject to applicable law, including the Nigeria Data Protection Act, 2023 (NDPA) and the
            Nigeria Data Protection Regulation (NDPR), you may have the right to access, correct,
            update, or delete your personal information, to object to or restrict certain processing,
            and to withdraw consent where processing is based on consent. To exercise these rights,
            contact us using the details below. You may also delete your account by contacting
            support.
          </p>
        </Section>

        <Section id="children" title="9. Children">
          <p>
            The Service is intended for users aged 18 and over. We do not knowingly collect personal
            information from children. If you believe a child has provided us with personal
            information, please contact us and we will take appropriate steps to remove it.
          </p>
        </Section>

        <Section id="changes" title="10. Changes to this Policy">
          <p>
            We may update this Policy from time to time. When we do, we will revise the &ldquo;Last
            updated&rdquo; date above and, where appropriate, notify you in the app. Your continued
            use of the Service after changes take effect means you accept the updated Policy.
          </p>
        </Section>

        <Section id="contact" title="11. Contact us">
          <p>
            If you have questions about this Policy or how we handle your information, contact IJ Ride
            support:
          </p>
          <ul className="list-none space-y-1">
            <li>
              Phone / WhatsApp:{" "}
              <a href={`tel:+234${SUPPORT_PHONE.slice(1)}`} className="font-semibold text-blue-600 hover:underline">
                {SUPPORT_PHONE}
              </a>
            </li>
            <li>
              Email:{" "}
              <a href={`mailto:${SUPPORT_EMAIL}`} className="font-semibold text-blue-600 hover:underline">
                {SUPPORT_EMAIL}
              </a>
            </li>
            <li>Location: Yola, Adamawa State, Nigeria</li>
          </ul>
        </Section>

        <footer className="border-t border-gray-200 pt-6 text-xs text-gray-400">
          © {new Date().getFullYear()} IJ Ride. All rights reserved.
        </footer>
      </main>
    </div>
  );
}
