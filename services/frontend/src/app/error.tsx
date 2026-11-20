"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return <div role="alert" className="service-error"><h1>This page could not be loaded</h1><p>Your irrigation information is unavailable. Try loading it again.</p><button onClick={reset} className="retry-button">Try again</button></div>;
}
