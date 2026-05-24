export function TestimonialSection() {
  return (
    <section className="bg-[#F4F2EC] px-8 py-25 text-center relative">
      <div className="max-w-310 mx-auto">
        <div className="font-serif text-[140px] leading-[0.6] text-[#DBD4BD] mb-3 select-none">
          "
        </div>
        <blockquote className="font-serif text-[clamp(26px,3vw,38px)] leading-snug tracking-[-0.012em] max-w-220 mx-auto text-ink m-0">
          Within two weeks of getting our lead list, we had three meetings booked
          with German distributors. One became our first EU customer.
        </blockquote>
        <div className="flex items-center justify-center gap-3 mt-[34px]">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[#C9B789] to-[#9D8A5C] flex items-center justify-center text-white font-semibold text-base">
            AK
          </div>
          <div className="text-left">
            <div className="font-semibold text-[15px] text-ink">Arben Krasniqi</div>
            <div className="text-[13px] text-ink-3">
              Owner, furniture manufacturer — Prizren, Kosovo
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
