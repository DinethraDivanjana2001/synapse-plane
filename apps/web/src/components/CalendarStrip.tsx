import type { TimeSlotOption } from "../lib/taskOutput";

interface Props {
  slots: TimeSlotOption[];
  selectedStart: string;
  onSelect?: (slot: TimeSlotOption) => void;
}

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function fmtDay(iso: string): string {
  return new Date(iso).toLocaleDateString([], { weekday: "short", day: "numeric", month: "short" });
}

// Every candidate dinner slot the calendar reported, free or busy. Busy slots
// come from the real calendar and can't be picked.
export function CalendarStrip({ slots, selectedStart, onSelect }: Props) {
  if (slots.length === 0) {
    return <p className="muted">No time slots were returned by the calendar.</p>;
  }

  const freeCount = slots.filter((s) => s.is_free).length;

  return (
    <div>
      <div className="slot-day">{fmtDay(slots[0].start_time)}</div>
      <div className="slot-row">
        {slots.map((slot) => {
          const isSelected = slot.start_time === selectedStart;
          const selectable = slot.is_free && Boolean(onSelect);
          const classes = [
            "slot",
            slot.is_free ? "slot-free" : "slot-busy",
            isSelected ? "slot-selected" : "",
          ]
            .filter(Boolean)
            .join(" ");
          return (
            <button
              type="button"
              className={classes}
              key={slot.start_time}
              disabled={!slot.is_free}
              onClick={selectable ? () => onSelect!(slot) : undefined}
              title={slot.is_free ? "Available — click to choose" : "Busy on your calendar"}
            >
              <span className="slot-time">{fmtTime(slot.start_time)}</span>
              <span className="slot-state">{slot.is_free ? "free" : "busy"}</span>
            </button>
          );
        })}
      </div>
      <p className="muted" style={{ fontSize: 12, marginTop: 8, marginBottom: 0 }}>
        {freeCount} of {slots.length} slots free &middot; each booking is 2 hours
        {onSelect ? " · click a free slot to change the time" : ""}
      </p>
    </div>
  );
}
