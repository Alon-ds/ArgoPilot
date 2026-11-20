const numbers = new Intl.NumberFormat("en", { maximumFractionDigits: 2 });
export const number = (value: number) => numbers.format(value);
export const date = (value: string) => new Intl.DateTimeFormat("en", { weekday: "short", month: "short", day: "numeric", timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
