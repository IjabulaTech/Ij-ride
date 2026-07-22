import type { Metadata, Viewport } from "next";
import { Geist } from "next/font/google";
import "./globals.css";

import { MaintenanceGate } from "@/components/ops/MaintenanceGate";
import { IosInstallPrompt } from "@/components/pwa/IosInstallPrompt";
import { PwaRegister } from "@/components/pwa/PwaRegister";
import { AuthProvider } from "@/lib/auth/AuthContext";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const SITE_DESCRIPTION =
  "Request rides, drive, and manage the IJ Ride fleet in Yola, Adamawa.";

export const metadata: Metadata = {
  title: { default: "IJ Ride", template: "%s | IJ Ride" },
  description: SITE_DESCRIPTION,
  applicationName: "IJ Ride",
  appleWebApp: {
    capable: true,
    title: "IJ Ride",
    // "default" keeps the iOS status bar as its own opaque bar so the sticky
    // white header never slides under the notch.
    statusBarStyle: "default",
  },
  icons: {
    icon: [
      { url: "/icons/favicon-16.png", sizes: "16x16", type: "image/png" },
      { url: "/icons/favicon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/icons/favicon-48.png", sizes: "48x48", type: "image/png" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
  openGraph: {
    title: "IJ Ride",
    description: SITE_DESCRIPTION,
    siteName: "IJ Ride",
    type: "website",
    images: [{ url: "/brand/og-image.png", width: 1200, height: 630, alt: "IJ Ride" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "IJ Ride",
    description: SITE_DESCRIPTION,
    images: ["/brand/og-image.png"],
  },
};

export const viewport: Viewport = {
  themeColor: "#ffffff",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} h-full antialiased`}>
      <body className="min-h-full">
        <AuthProvider>
          <MaintenanceGate>{children}</MaintenanceGate>
        </AuthProvider>
        <PwaRegister />
        <IosInstallPrompt />
      </body>
    </html>
  );
}
