import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { LandingNav } from "@/components/landing/landing-nav";
import { HeroSection } from "@/components/landing/hero-section";
import { ShowcaseSection } from "@/components/landing/showcase-section";
import { SocialProofStrip } from "@/components/landing/social-proof-strip";
import { HowItWorks } from "@/components/landing/how-it-works";
import { FeaturesSection } from "@/components/landing/features-section";
import { PricingSection } from "@/components/landing/pricing-section";
import { TestimonialSection } from "@/components/landing/testimonial-section";
import { FinalCTA } from "@/components/landing/final-cta";
import { LandingFooter } from "@/components/landing/landing-footer";

export default async function HomePage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (user) redirect("/reports");

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <LandingNav />
      <main>
        <HeroSection />
        <ShowcaseSection />
        <SocialProofStrip />
        <HowItWorks />
        <FeaturesSection />
        <PricingSection />
        <TestimonialSection />
        <FinalCTA />
      </main>
      <LandingFooter />
    </div>
  );
}
