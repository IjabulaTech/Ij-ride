import { AuthPageFrame } from "@/components/auth/AuthPageFrame";
import { RegisterForm } from "@/components/auth/RegisterForm";

export const metadata = { title: "Create account" };

export default function RegisterPassengerPage() {
  return (
    <AuthPageFrame heading="Create your passenger account">
      <RegisterForm role="passenger" />
    </AuthPageFrame>
  );
}
