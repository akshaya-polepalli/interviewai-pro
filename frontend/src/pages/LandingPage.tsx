import { motion } from "framer-motion";
import {
  ArrowRight,
  BrainCircuit,
  Code2,
  Map as MapIcon,
  Mic2,
  Route,
  Sparkles,
} from "lucide-react";
import { Link } from "react-router-dom";

const modules = [
  {
    icon: BrainCircuit,
    title: "AI mock interviews",
    body: "Technical, behavioral, HR, and voice rounds with structured scoring.",
  },
  {
    icon: Code2,
    title: "Live coding lab",
    body: "Seeded problems, restricted Python runner, and accepted-submission history.",
  },
  {
    icon: Mic2,
    title: "Voice interviewer",
    body: "Browser TTS/STT plus optional Whisper transcription into the same evaluator.",
  },
  {
    icon: Sparkles,
    title: "AI coach",
    body: "Multi-day study plans from analytics weak spots, with mentoring chat.",
  },
  {
    icon: MapIcon,
    title: "Company roadmaps",
    body: "Google, Amazon, Meta, and more — milestones that auto-track your progress.",
  },
  {
    icon: Route,
    title: "ATS + reports",
    body: "Resume scoring, PDF exports, achievements, and an admin console.",
  },
];

export function LandingPage() {
  return (
    <div className="space-y-24 pb-8">
      <section className="relative min-h-[70vh] overflow-hidden pt-4 sm:pt-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="relative z-10 max-w-3xl"
        >
          <p className="font-display text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
            InterviewAI <span className="text-accent">Pro</span>
          </p>
          <h1 className="mt-6 font-display text-4xl font-semibold leading-[1.1] tracking-tight text-ink sm:text-5xl lg:text-6xl">
            Interview prep built like a real SaaS product.
          </h1>
          <p className="mt-5 max-w-xl text-lg text-ink-muted">
            Auth, workers, ATS, voice mocks, coding, coach, and company tracks — one monorepo you
            can demo and defend in system-design interviews.
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <Link to="/signup" className="btn-primary">
              Get started
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link to="/login" className="btn-ghost">
              Sign in · demo account
            </Link>
          </div>
        </motion.div>

        <motion.div
          aria-hidden
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2, duration: 0.9 }}
          className="pointer-events-none absolute inset-y-0 right-[-20%] hidden w-[70%] lg:block"
        >
          <div className="absolute inset-8 rounded-[2rem] border border-white/10 bg-gradient-to-br from-accent/20 via-transparent to-sky-500/10" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_40%,rgba(45,212,191,0.25),transparent_55%)]" />
        </motion.div>
      </section>

      <section className="space-y-6 border-t border-white/10 pt-14">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.45 }}
        >
          <h2 className="font-display text-2xl text-ink sm:text-3xl">What ships in the box</h2>
          <p className="mt-2 max-w-2xl text-ink-muted">
            Thirteen production-shaped modules — not a CRUD tutorial.
          </p>
        </motion.div>
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
          {modules.map((item, index) => (
            <motion.article
              key={item.title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ delay: index * 0.05, duration: 0.4 }}
              className="border-t border-white/10 pt-5"
            >
              <item.icon className="mb-3 h-5 w-5 text-accent" />
              <h3 className="font-display text-lg text-ink">{item.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-muted">{item.body}</p>
            </motion.article>
          ))}
        </div>
      </section>

      <section className="space-y-4 border-t border-white/10 pt-14">
        <h2 className="font-display text-2xl text-ink">Try the demo</h2>
        <p className="max-w-2xl text-ink-muted">
          After seeding, sign in as{" "}
          <code className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-sm text-accent">
            demo@interviewai.local
          </code>{" "}
          /{" "}
          <code className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-sm text-accent">
            DemoPass1
          </code>
          . Preloaded interview, coding accept, coach plan, and Google roadmap enrollment.
        </p>
        <Link to="/login" className="btn-primary inline-flex">
          Open sign in
          <ArrowRight className="h-4 w-4" />
        </Link>
      </section>
    </div>
  );
}
