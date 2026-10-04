import Link from "next/link";
import Image from "next/image";

const steps = [
  ["01", "Describe", "Say what the group wants, in plain language."],
  ["02", "Invite", "Share a short room code. No account needed."],
  ["03", "Swipe", "Everyone chooses privately on the same list."],
  ["04", "Match", "A Python engine ranks where you actually agree."],
];

export default function HomePage() {
  return (
    <div className="landing-enter grid items-center gap-12 pt-6 lg:grid-cols-[1.1fr_0.9fr] lg:pt-12">
      <section>
        <p className="eyebrow">Group dinner, settled</p>
        <h1 className="header1">Stop arguing. Let the group decide.</h1>
        <p className="lead-copy">
          Describe the night, invite your friends, and swipe the same restaurants. Nomly finds the place your table
          actually agrees on.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/loading/create" className="button-primary rounded-full px-6 py-3 shadow-card">
            Create a dinner
          </Link>
          <Link href="/loading/join" className="button-secondary rounded-full px-6 py-3">
            Join with a code
          </Link>
        </div>
      </section>

      <section className="relative mx-auto h-[420px] w-full max-w-md">
        <Image
          src="/assets/IMG_8293.webp"
          alt="Nomly chef mascot holding a fork"
          fill
          sizes="(max-width: 448px) 100vw, 448px"
          className="-translate-y-6 scale-110 object-contain"
        />
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:col-span-2 lg:grid-cols-4">
        {steps.map(([number, title, copy]) => (
          <article key={number} className="feature-card rounded-3xl border border-line bg-card/80 p-5">
            <p className="step-number">{number}</p>
            <h2 className="header2">{title}</h2>
            <p className="step-copy">{copy}</p>
          </article>
        ))}
      </section>
    </div>
  );
}
