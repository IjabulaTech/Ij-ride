import type { ReactNode } from "react";

import { BrandLogo } from "@/components/ui/BrandLogo";
import { Card } from "@/components/ui/Card";

export function AuthPageFrame({
  heading,
  children,
  below,
}: {
  heading: string;
  children: ReactNode;
  /** Optional content rendered under the card (e.g. the home image marquee). */
  below?: ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4 py-8">
      <div className="w-full max-w-md space-y-6">
        <div className="flex flex-col items-center text-center">
          <BrandLogo size={72} className="shadow-sm" />
          <h1 className="mt-3 text-2xl font-extrabold text-gray-900">IJ Ride</h1>
          <p className="mt-1 text-sm text-gray-600">{heading}</p>
        </div>
        <Card className="p-6">{children}</Card>
        {below}
      </div>
    </div>
  );
}
