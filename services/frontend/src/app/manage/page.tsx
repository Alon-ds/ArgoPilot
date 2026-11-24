import Link from "next/link";
import { config } from "@/lib/config";
import { getCrops, getEmitters, getFarms, getSoils } from "@/lib/services";
import { AddFarmForm } from "@/components/add-farm-form";
import { AddPlotForm } from "@/components/add-plot-form";
import { ServiceError } from "@/components/service-error";

export const metadata = { title: "Add farms and plots" };

export default async function ManagePage() {
  const [farms, crops, soils, emitters] = await Promise.all([getFarms(), getCrops(), getSoils(), getEmitters()]);
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: config.PLAN_TIMEZONE, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
  const catalogues = crops.ok && soils.ok && emitters.ok;
  return <>
    <div className="page-intro">
      <h1>Add farms and plots</h1>
      <p>New records are written to the registry service, which stores them in its database.</p>
      <Link href="/" className="back-link" prefetch={false}>‹ Back to your farms</Link>
    </div>
    {!farms.ok && <ServiceError message={farms.message} title="Farms are unavailable" />}
    {!catalogues && <ServiceError message="The crop, soil or emitter catalogue could not be read, so a plot cannot be added safely." title="Catalogues are unavailable" />}
    <section className="entry-section">
      <h2>New farm</h2>
      <AddFarmForm />
    </section>
    <section className="entry-section">
      <h2>New plot</h2>
      {farms.ok && catalogues
        ? <AddPlotForm farms={farms.data} crops={crops.data} soils={soils.data} emitters={emitters.data} today={today} />
        : <p className="empty">The form opens once the registry answers.</p>}
    </section>
  </>;
}
