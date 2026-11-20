import Link from "next/link";
import { getPlan, getPlot } from "@/lib/services";
import { IrrigationPlan } from "@/components/plan";
import { ServiceError } from "@/components/service-error";
export const metadata = { title: "Plot irrigation plan" };
export default async function PlotPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [plot, plan] = await Promise.all([getPlot(id), getPlan(id)]);
  return <>
    <Link href="/" className="back-link">‹ All farms</Link>
    <h1 className="plot-title">{plot.ok ? plot.data.name : "Plot irrigation plan"}</h1>
    {plan.ok ? <IrrigationPlan plan={plan.data} /> : <ServiceError title="Irrigation plan unavailable" message={plan.message} />}
    {!plot.ok && <div className="metadata-error"><ServiceError title="Plot details unavailable" message={plot.message} /></div>}
  </>;
}
