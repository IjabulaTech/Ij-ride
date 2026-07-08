/* eslint-disable @next/next/no-img-element */

/** The official IJ Ride mark (the "ij" monogram). The source art sits on
 * white, so a subtle rounded tile reads cleanly on both the white header
 * and the gray auth surfaces. */
export function BrandLogo({
  size = 32,
  className = "",
  rounded = true,
}: {
  size?: number;
  className?: string;
  rounded?: boolean;
}) {
  return (
    <img
      src="/brand/logo-mark.png"
      alt="IJ Ride"
      width={size}
      height={size}
      className={`object-contain ${rounded ? "rounded-lg border border-gray-100" : ""} ${className}`}
      style={{ width: size, height: size }}
    />
  );
}
