import { useEffect, useState } from "react";

// Counts down to a real expires_at timestamp from the API — not a fabricated TTL.
export function CountdownTimer({ expiresAt }: { expiresAt: string }) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const remainingMs = new Date(expiresAt).getTime() - now;
  if (remainingMs <= 0) {
    return <span className="countdown">Expired</span>;
  }

  const hours = Math.floor(remainingMs / 3_600_000);
  const minutes = Math.floor((remainingMs % 3_600_000) / 60_000);
  const seconds = Math.floor((remainingMs % 60_000) / 1000);

  return (
    <span className="countdown">
      Expires in {hours}h {minutes}m {seconds}s
    </span>
  );
}
