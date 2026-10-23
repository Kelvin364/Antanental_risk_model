import { PlainScreen } from "@/components/Screen";

export default function Page() {
  return (
    <PlainScreen id="about" title="About" lead="What this prototype is, and what it is not.">
      <div className="card space-y-3">
        <p>
          This is a research prototype from a capstone study at the African Leadership University. It
          estimates the chance of low birth weight from registration details and two antenatal visits,
          using a model developed on one publicly released Tanzanian dataset.
        </p>
        <p>
          <b>Synthetic cases only.</b> No real pregnancy may be entered. The system stores no names or
          identifiers, and every case must carry the synthetic flag.
        </p>
        <p>
          <b>Not a medical device.</b> The label, probability and rank are research estimates. They have not
          been validated for any pregnancy and must not be used to decide care.
        </p>
        <p>
          <b>How confident the label is.</b> Each assessment shows how often the label was right on the
          development records, with intervals, and whether the case&rsquo;s own interval crosses the
          threshold. Most pregnancies labelled &ldquo;likely&rdquo; did not have low birth weight.
        </p>
        <p>
          <b>Accounts.</b> Administrators create researcher accounts. Researchers see only the cases they
          registered. Sign in is required for every case, visit, assessment and caseload.
        </p>
      </div>
    </PlainScreen>
  );
}
