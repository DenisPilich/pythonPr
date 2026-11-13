import { Link } from "react-router-dom";

import { Button, Card } from "../components/ui";

export default function NotFoundPage() {
  return (
    <Card className="corner-frame mx-auto max-w-xl p-8">
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2 text-[9px] uppercase tracking-[0.18em] text-slate-500">
        <span className="h-2 w-2 border border-rose-500/60 bg-rose-500/20" />
        radar://error
        <span className="ml-auto">404</span>
      </div>

      <div className="mt-5 font-mono text-[11px] leading-6 text-slate-400">
        <p>
          <span className="text-emerald-400">$</span> cd /requested-route
        </p>
        <p className="text-rose-300">
          bash: cd: /requested-route: No such file or directory
        </p>
      </div>

      <p className="mt-6 font-display text-7xl leading-none text-white">
        4<span className="text-sky-400">0</span>4
      </p>
      <h1 className="mt-2 font-display text-3xl text-slate-100">
        page not found
      </h1>
      <p className="mt-2 text-[11px] text-slate-400">
        The route does not exist. The radar is still scanning in the background.
      </p>

      <Link to="/" className="mt-6 inline-block">
        <Button>[ back to radar ]</Button>
      </Link>
    </Card>
  );
}
