import Link from "next/link";

const steps = [
  ["01", "Describe", "Say what the group wants, in plain language."],
  ["02", "Invite", "Share a short room code. No accounts."],
  ["03", "Swipe", "Everyone chooses privately on the same list."],
  ["04", "Match", "A Python engine ranks where you actually agree."],
];

export default function HomePage() {
  return (
    <div className="grid items-center gap-12 pt-6 lg:grid-cols-[1.1fr_0.9fr] lg:pt-12">
      <section>
        <p className="text-sm font-medium uppercase tracking-[0.22em] text-chili">Group dinner, settled</p>
        <h1 className="mt-4 max-w-xl font-serif text-5xl leading-[1.05] text-ink sm:text-7xl">
          Stop arguing. Let the group decide.
        </h1>
        <p className="mt-6 max-w-lg text-lg leading-relaxed text-ink-soft">
          Describe the night, invite your friends, and swipe the same restaurants. DineOff finds the place your table
          actually agrees on.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/create" className="rounded-full bg-chili px-6 py-3 text-white shadow-card">
            Create a dinner
          </Link>
          <Link href="/join" className="rounded-full border border-ink/15 bg-card px-6 py-3">
            Join with a code
          </Link>
        </div>
      </section>

      <section className="relative mx-auto h-[420px] w-full max-w-md">
        <article className="absolute left-6 top-10 w-72 rotate-[-8deg] rounded-3xl border border-line bg-[#f0d3c2] p-5 shadow-card">
          <p className="text-xs uppercase tracking-[0.18em] text-ink-soft">Korean</p>
          <h2 className="mt-3 font-serif text-3xl">Han River BBQ</h2>
          <p className="mt-3 text-sm text-ink-soft">Tabletop grills for the whole group.</p>
        </article>
        <article className="absolute right-0 top-24 w-72 rotate-[7deg] rounded-3xl border border-line bg-card p-5 shadow-card">
          <p className="text-xs uppercase tracking-[0.18em] text-ink-soft">Japanese</p>
          <h2 className="mt-3 font-serif text-3xl">Kinjo Sushi</h2>
          <p className="mt-3 text-sm text-ink-soft">Casual counter. Short menu. Easy yes.</p>
        </article>
        <div className="absolute bottom-4 left-8 right-8 rounded-full bg-ink px-5 py-4 text-center text-paper">
          80% group match
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:col-span-2 lg:grid-cols-4">
        {steps.map(([number, title, copy]) => (
          <article key={number} className="rounded-3xl border border-line bg-card/80 p-5">
            <p className="text-xs tracking-[0.18em] text-gold">{number}</p>
            <h2 className="mt-3 font-serif text-2xl">{title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-ink-soft">{copy}</p>
          </article>
        ))}
      </section>
    </div>
  );
}
