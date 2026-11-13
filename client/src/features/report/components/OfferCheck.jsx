import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { offerVerdict, parseAmount, pay } from "../lib/pay.js";
import RangeBar from "./RangeBar.jsx";

// "Check my offer": where a planned salary or hourly rate lands against current openings.
export default function OfferCheck({ r }) {
  const [text, setText] = useState("");
  const [amount, setAmount] = useState(null);
  const [problem, setProblem] = useState(null);
  const hourly = r.unit === "hour";
  const what = hourly ? "hourly rate" : "salary";

  const check = (e) => {
    e.preventDefault();
    const n = parseAmount(text);
    if (n == null) {
      setAmount(null);
      setProblem(`Enter the ${hourly ? "hourly rate" : "yearly salary"} as a number, for example ${hourly ? "18.50" : "52,000"}.`);
      return;
    }
    setProblem(null);
    setAmount(n);
    setText(pay(n, r.unit));
  };

  const verdict = amount != null && offerVerdict(amount, r.pay, r.unit);
  return (
    <Card as="section" className="mh-card" data-reveal>
      <h2>Check my offer</h2>
      <p className="mh-muted">Enter the {what} you're planning to offer and see where it lands.</p>
      <form className="mh-offer" onSubmit={check}>
        <div className="mh-field">
          <Label htmlFor="offer-amount">Planned {what}</Label>
          <Input id="offer-amount" inputMode="decimal" placeholder={hourly ? "$18.00" : "$52,000"} value={text}
            onChange={(e) => setText(e.target.value)}
            aria-invalid={problem ? true : undefined} aria-describedby={problem ? "offer-problem" : undefined} />
        </div>
        <Button type="submit" className="mh-btn mh-btn-teal">Check</Button>
      </form>
      {problem && <p id="offer-problem" className="mh-error" role="alert">{problem}</p>}
      {verdict && (
        <>
          <RangeBar p={r.pay} marker={amount} />
          <p className="mh-offer-verdict" role="status"><strong>{verdict[0]}</strong> {verdict[1]}</p>
        </>
      )}
    </Card>
  );
}
