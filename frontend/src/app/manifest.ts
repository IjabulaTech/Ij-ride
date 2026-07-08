import type { MetadataRoute } from "next";

// Served at /manifest.webmanifest and linked automatically by Next.
// Launch colours match the logo's dark ground so the Android splash and the
// icon read as one piece.
export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "IJ Ride",
    short_name: "IJ Ride",
    description: "Request rides, drive, and manage the IJ Ride fleet in Yola, Adamawa.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#ffffff",
    theme_color: "#ffffff",
    categories: ["travel", "transportation", "navigation"],
    icons: [
      { src: "/icons/favicon-48.png", sizes: "48x48", type: "image/png" },
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      {
        src: "/icons/icon-maskable-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "maskable",
      },
      {
        src: "/icons/icon-maskable-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
