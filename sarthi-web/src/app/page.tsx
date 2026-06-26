import { AgentVsChatbot } from "../components/landing/AgentVsChatbot";
import { FeatureGrid } from "../components/landing/FeatureGrid";
import { Footer } from "../components/landing/Footer";
import { Hero } from "../components/landing/Hero";
import { HowItWorks } from "../components/landing/HowItWorks";
import { MarketingNav } from "../components/landing/MarketingNav";

export default function Home() {
  return (
    <>
      <MarketingNav />
      <main>
        <Hero />
        <AgentVsChatbot />
        <FeatureGrid />
        <HowItWorks />
      </main>
      <Footer />
    </>
  );
}
