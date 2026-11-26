import { Badge } from "@/components/ui/badge";
import type { Plan } from "@/lib/services";
import { number, date, hoursMinutes } from "@/lib/format";
function Stale() { return <Badge variant="outline" className="stale">Older forecast</Badge>; }
export function IrrigationPlan({ plan }: { plan: Plan }) {
  const today = plan.days[0];
  const last = plan.days[plan.days.length - 1];
  return <>
    <section className="today" aria-labelledby="recommendation">
      <p className="today-date">Today · {date(today.date)}</p>
      {today.irrigation_in_progress ? <>
        <h2 id="recommendation">Irrigation in progress</h2>
        <dl className="today-progress">
          <div><dt>Scheduled today</dt><dd>{number(today.litres)} L · {hoursMinutes(today.run_minutes)}</dd></div>
          <div><dt>Remaining water</dt><dd>{number(today.remaining_litres)} L · {hoursMinutes(today.remaining_run_minutes)}</dd></div>
          <div><dt>Predicted soil water</dt><dd>{number(today.bucket_pct)}%</dd></div>
        </dl>
        <p className="today-volume">Continues tomorrow</p>
      </> : <>
        <h2 id="recommendation">{today.run_minutes === 0 ? "No irrigation today" : <>Water for <strong>{number(today.run_minutes)}</strong> minutes</>}</h2>
        <p className="today-volume">{number(today.litres)} litres{today.run_minutes > 0 ? " through your drip system" : " to apply"}</p>
      </>}
      {today.capacity_warning && <div className="today-warning"><strong>Hydraulic capacity insufficient.</strong><p>The irrigation system cannot supply enough water to compensate for the current estimated crop demand.</p></div>}
      {today.stale && <div className="today-stale"><Stale /><p>Based on a cached forecast. These numbers may change when fresh weather is available.</p></div>}
    </section>
    {last.irrigation_in_progress && <aside className="horizon-note" aria-label="Forecast horizon">
      <strong>Irrigation continues beyond the forecast period.</strong>
      <p>Remaining estimated water: {number(last.remaining_litres)} L · about {hoursMinutes(last.remaining_run_minutes)}. The forecast only covers seven days.</p>
    </aside>}
    <section className="weekly" aria-labelledby="week-heading">
      <h2 id="week-heading">The next 7 days</h2>
      <p className="section-description">Daily irrigation, weather demand and water remaining in the soil.</p>
      <table className="plan-table">
        <caption className="sr-only">Seven-day irrigation plan. ET0 and soil water in millimetres, Kc is the crop factor.</caption>
        <colgroup><col className="day-column" /><col className="irrigation-column" /><col /></colgroup>
        <thead><tr><th scope="col">Day</th><th scope="col">Irrigation</th><th scope="col">Weather &amp; soil</th></tr></thead>
        <tbody>{plan.days.map((day, index) => <tr key={day.date} className={index === 0 ? "today-row" : undefined}>
          <th scope="row">{index === 0 && <span className="table-today">Today</span>}<time dateTime={day.date}>{date(day.date)}</time></th>
          <td><strong>{day.run_minutes === 0 ? "No irrigation" : `${number(day.run_minutes)} min`}</strong><span>{number(day.litres)} L</span>{day.stale && <Stale />}</td>
          <td><span>ET0 {number(day.et0_mm)} mm</span><span>Kc {number(day.kc)}</span><span>Soil {number(day.bucket_mm)} mm ({Math.round(day.bucket_pct)}%)</span></td>
        </tr>)}</tbody>
      </table>
      <ul className="table-note">
        <li>ET0: water lost to the weather.</li>
        <li>Kc: crop factor.</li>
        <li>Soil: water remaining at the end of the day, and as a percent of a full soil.</li>
      </ul>
    </section>
  </>;
}
