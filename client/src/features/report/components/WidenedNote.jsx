import React from "react";
import { Info } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

// Says plainly when the search was widened (state → region → national) for lack of listed pay.
export default function WidenedNote({ note }) {
  const [first, ...rest] = note.split(". ");
  return (
    <Alert role="status" className="mh-note">
      <Info className="size-5" aria-hidden="true" />
      <AlertDescription className="text-inherit">
        <span><strong>{first}.</strong> {rest.join(". ")}</span>
      </AlertDescription>
    </Alert>
  );
}
