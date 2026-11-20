import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
export function ServiceError({ message, title = "Unable to load this information" }: { message: string; title?: string }) {
  return <Alert className="service-error"><AlertTitle className="line-clamp-none"><h2>{title}</h2></AlertTitle><AlertDescription><p>{message}</p><p className="mt-2">Refresh this page to try again.</p></AlertDescription></Alert>;
}
