"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export function LoadingScreen({ destination }: { destination: string }) {
  const router = useRouter();
  const [isLeaving, setIsLeaving] = useState(false);

  useEffect(() => {
    let navigationTimer: number | undefined;
    const loadingTimer = window.setTimeout(() => {
      setIsLeaving(true);
      navigationTimer = window.setTimeout(() => router.replace(destination), 450);
    }, 5000);

    return () => {
      window.clearTimeout(loadingTimer);
      if (navigationTimer !== undefined) window.clearTimeout(navigationTimer);
    };
  }, [destination, router]);

  return (
    <section
      className={`mx-auto flex min-h-[70vh] max-w-6xl flex-col items-center justify-center gap-2 px-5 text-center transition-all duration-500 ease-out motion-reduce:transition-none ${
        isLeaving ? "translate-y-2 opacity-0" : "translate-y-0 opacity-100"
      }`}
    >
      <Image
        src="/assets/chomp_loading.gif"
        alt="Nomly loading animation"
        width={320}
        height={320}
        unoptimized
        className="h-80 w-80 object-contain"
      />
      <h1 className="header2 !mt-0">Loading . . .</h1>
    </section>
  );
}