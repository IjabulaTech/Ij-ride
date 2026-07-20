import { Card } from "@/components/ui/Card";
import {
  SUPPORT_PHONE_LOCAL,
  SUPPORT_SMS_HREF,
  SUPPORT_TEL_HREF,
  SUPPORT_WHATSAPP_HREF,
} from "@/lib/support";

/** Direct ways to reach a human, alongside the in-app chat. */
export function SupportContactCard() {
  return (
    <Card className="space-y-3">
      <div>
        <h3 className="font-semibold text-gray-900">Prefer to call or message?</h3>
        <p className="mt-0.5 text-sm text-gray-600">
          Customer support:{" "}
          <span className="font-mono font-semibold text-gray-900">{SUPPORT_PHONE_LOCAL}</span>
        </p>
      </div>
      <div className="grid grid-cols-3 gap-2">
        <a
          href={SUPPORT_TEL_HREF}
          className="flex flex-col items-center gap-1 rounded-lg bg-blue-600 px-3 py-2.5 text-xs font-semibold text-white hover:bg-blue-700"
        >
          <span aria-hidden className="text-base">
            📞
          </span>
          Call
        </a>
        <a
          href={SUPPORT_WHATSAPP_HREF}
          target="_blank"
          rel="noopener noreferrer"
          className="flex flex-col items-center gap-1 rounded-lg bg-emerald-600 px-3 py-2.5 text-xs font-semibold text-white hover:bg-emerald-700"
        >
          <span aria-hidden className="text-base">
            💬
          </span>
          WhatsApp
        </a>
        <a
          href={SUPPORT_SMS_HREF}
          className="flex flex-col items-center gap-1 rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-xs font-semibold text-gray-700 hover:bg-gray-50"
        >
          <span aria-hidden className="text-base">
            ✉️
          </span>
          SMS
        </a>
      </div>
    </Card>
  );
}
