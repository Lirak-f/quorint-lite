"use client";

import { useEffect } from "react";
import { initializePaddle } from "@paddle/paddle-js";

export function PaddleProvider() {
  useEffect(() => {
    const token = process.env.NEXT_PUBLIC_PADDLE_CLIENT_TOKEN;
    const env = process.env.NEXT_PUBLIC_PADDLE_ENV as "sandbox" | "production" | undefined;

    if (!token) return;

    initializePaddle({
      environment: env ?? "sandbox",
      token,
    });
  }, []);

  return null;
}
