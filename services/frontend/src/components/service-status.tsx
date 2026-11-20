import { getHealth } from "@/lib/services";
export async function ServiceStatus() {
  const health = await getHealth();
  return <footer className="service-status" aria-label="Service status">
    <span>Service status</span>
    <ul>{health.map(({ service, up }) => <li key={service}><span className={`status-dot ${up ? "up" : "down"}`} aria-hidden="true" />{service}: {up ? "up" : "down"}</li>)}</ul>
  </footer>;
}
