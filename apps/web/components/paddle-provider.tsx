"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { initializePaddle, type Paddle } from "@paddle/paddle-js";

const PaddleContext = createContext<Paddle | undefined>(undefined);

export function usePaddle() {
  return useContext(PaddleContext);
}

export function PaddleProvider({ children }: { children: ReactNode }) {
  const [paddle, setPaddle] = useState<Paddle | undefined>(undefined);

  useEffect(() => {
    const token = process.env.NEXT_PUBLIC_PADDLE_CLIENT_TOKEN;
    const env = process.env.NEXT_PUBLIC_PADDLE_ENV as "sandbox" | "production" | undefined;
    if (!token) return;
    initializePaddle({ environment: env ?? "sandbox", token }).then(setPaddle);
  }, []);

  return <PaddleContext.Provider value={paddle}>{children}</PaddleContext.Provider>;
}
