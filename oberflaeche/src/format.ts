// Zeit- und Datumsformate der Oberfläche, englisch wie der Entwurf

const MONATE = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export const nr = (n: number) => String(n).padStart(2, "0");

export const uhrzeit = (d: Date) => `${nr(d.getHours())}:${nr(d.getMinutes())}`;

export function laufzeit(sekunden: number) {
  const s = Math.max(0, Math.floor(sekunden));
  return `${Math.floor(s / 60)}:${nr(s % 60)}`;
}

export function dauer(ms: number) {
  const s = Math.max(0, Math.round(ms / 1000));
  return s < 60 ? `${s} s` : `${Math.floor(s / 60)} min ${s % 60} s`;
}

// "2026-10-30" -> "30 Oct 2026"
export function datum(iso: string | null) {
  const t = iso ? /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso) : null;
  return t ? `${Number(t[3])} ${MONATE[Number(t[2]) - 1]} ${t[1]}` : null;
}
