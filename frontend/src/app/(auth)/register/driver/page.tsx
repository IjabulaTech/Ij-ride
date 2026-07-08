import { AuthPageFrame } from "@/components/auth/AuthPageFrame";
import { RegisterForm } from "@/components/auth/RegisterForm";

export const metadata = { title: "Drive with IJ Ride" };

export default function RegisterDriverPage() {
  return (
    <AuthPageFrame heading="Sign up to drive with IJ Ride">
      <RegisterForm role="driver" />
    </AuthPageFrame>
  );
}
