const numbers = new Intl.NumberFormat("en", { maximumFractionDigits: 2 });
export const number = (value: number) => numbers.format(value);
export const hoursMinutes = (minutes: number) => {
  const total = Math.round(minutes);
  const h = Math.floor(total / 60);
  const m = total % 60;
  return h > 0 ? `${number(h)}h ${m}m` : `${m}m`;
};
export const date = (value: string) => new Intl.DateTimeFormat("en", { weekday: "short", month: "short", day: "numeric", timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
