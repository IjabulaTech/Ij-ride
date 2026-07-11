/* eslint-disable @next/next/no-img-element */

/**
 * A small band of images that scrolls sideways forever. The track renders the
 * images twice back-to-back and animates by -50%, so the loop is seamless.
 *
 * The keyframes live in a scoped <style> here rather than globals.css: Tailwind
 * v4's CSS pipeline strips unreferenced custom rules from the global sheet, so
 * inlining guarantees the animation ships in every environment. Respects
 * prefers-reduced-motion. Pure CSS — no JS timers.
 */
const SHOWCASE_IMAGES: { src: string; alt: string }[] = [
  { src: "/showcase/keke.jpg", alt: "Keke tricycle" },
  { src: "/showcase/motor-1.jpg", alt: "Motorcycle" },
  { src: "/showcase/motor-2.jpg", alt: "Motorcycle" },
];

const MARQUEE_CSS = `
@keyframes ijride-marquee {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}
.ijride-marquee-track {
  display: flex;
  width: max-content;
  animation: ijride-marquee 24s linear infinite;
}
@media (prefers-reduced-motion: reduce) {
  .ijride-marquee-track { animation: none; }
}
`;

export function ImageMarquee() {
  // Duplicate the list so the -50% translate lands exactly on a repeat.
  const loop = [...SHOWCASE_IMAGES, ...SHOWCASE_IMAGES];

  return (
    <div
      className="overflow-hidden rounded-xl border border-gray-200 bg-white py-3"
      aria-label="IJ Ride vehicles"
    >
      <style>{MARQUEE_CSS}</style>
      <div className="ijride-marquee-track gap-4 px-2">
        {loop.map((img, i) => (
          <img
            key={i}
            src={img.src}
            alt={img.alt}
            aria-hidden={i >= SHOWCASE_IMAGES.length}
            loading="lazy"
            className="h-24 w-40 shrink-0 rounded-lg object-cover"
          />
        ))}
      </div>
    </div>
  );
}
