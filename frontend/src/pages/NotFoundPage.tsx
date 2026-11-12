import { Link } from "react-router-dom";

import { Button, Card } from "../components/ui";

export default function NotFoundPage() {
  return (
    <Card className="mx-auto max-w-lg p-10 text-center">
      <p className="text-5xl font-semibold text-sky-400">404</p>
      <h1 className="mt-3 text-xl font-semibold text-white">Page not found</h1>
      <p className="mt-2 text-sm text-slate-400">
        The route does not exist. The radar is still running in the background.
      </p>
      <Link to="/" className="mt-6 inline-block">
        <Button>Back to overview</Button>
      </Link>
    </Card>
  );
}
