"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getToken, getBusinessId } from "@/lib/api";

export default function RootPage() {
  const router = useRouter();
  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    const bizId = getBusinessId();
    if (!bizId) {
      router.replace("/onboarding");
      return;
    }
    router.replace("/home");
  }, [router]);

  return (
    <div className="flex items-center justify-center h-screen">
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}
