import Link from "next/link";
import { getFarms, getPlots } from "@/lib/services";
import { number } from "@/lib/format";
import { ServiceError } from "@/components/service-error";
export default async function HomePage() {
  const [farms, plots] = await Promise.all([getFarms(), getPlots()]);
  return <>
    <div className="page-intro"><h1>Your farms</h1><p>Choose a plot to see when and how much to water.</p>
      <Link href="/manage" className="back-link" prefetch={false}>Add a farm or plot ›</Link></div>
    {!farms.ok && <ServiceError message={farms.message} title="Farms are unavailable" />}
    {!plots.ok && <ServiceError message={plots.message} title="Plots are unavailable" />}
    {farms.ok && farms.data.length === 0 && <p className="empty">No farms registered yet. <Link href="/manage" prefetch={false} className="plot-link-label">Add your first farm</Link>.</p>}
    {farms.ok && farms.data.map((farm) => {
      const farmPlots = plots.ok ? plots.data.filter((plot) => plot.farm_id === farm.id) : [];
      return <section className="farm" key={farm.id} aria-labelledby={`farm-${farm.id}`}>
        <div className="farm-heading"><h2 id={`farm-${farm.id}`}>{farm.name}</h2>{plots.ok && <span>{farmPlots.length} {farmPlots.length === 1 ? "plot" : "plots"}</span>}</div>
        {plots.ok && farmPlots.length === 0 && <p className="empty">No plots registered for this farm.</p>}
        <ul className="plot-list">{farmPlots.map((plot) => <li key={plot.id}><Link href={`/plots/${encodeURIComponent(plot.id)}`} prefetch={false}>
          <div><h3>{plot.name}</h3><p>{plot.crop_id.replaceAll("_", " ").replaceAll("-", " ")} · {number(plot.area_m2)} m²</p></div>
          <span className="plot-link-label">View plan <span aria-hidden="true">›</span></span>
        </Link></li>)}</ul>
      </section>;
    })}
  </>;
}
