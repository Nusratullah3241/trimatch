export default function Settings() {
  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <h1 className="text-xl font-semibold">Tolerances</h1>
        <p className="text-sm text-muted mt-1">
          How far a figure can drift before someone needs to look at it.
        </p>
      </div>

      <div className="card divide-y divide-rule">
        <div className="p-5 flex items-baseline justify-between">
          <div>
            <div className="text-sm font-medium">Price drift</div>
            <p className="text-xs text-muted mt-1">
              An invoiced rate above the ordered rate by more than this is flagged.
            </p>
          </div>
          <span className="figure text-lg">2.0%</span>
        </div>

        <div className="p-5 flex items-baseline justify-between">
          <div>
            <div className="text-sm font-medium">Minimum amount</div>
            <p className="text-xs text-muted mt-1">
              Small drifts are ignored below this figure, even when the percentage looks large.
            </p>
          </div>
          <span className="figure text-lg">500.00</span>
        </div>

        <div className="p-5 flex items-baseline justify-between">
          <div>
            <div className="text-sm font-medium">Quantity drift</div>
            <p className="text-xs text-muted mt-1">
              Being billed for more than arrived is never acceptable, so this sits at zero.
            </p>
          </div>
          <span className="figure text-lg">0.0%</span>
        </div>
      </div>

      <div className="card p-5 bg-rule/20">
        <div className="eyebrow">Changing these</div>
        <p className="text-sm mt-2">
          Edit PRICE_TOLERANCE_PCT and ABSOLUTE_TOLERANCE_AMOUNT in the backend .env file, then
          restart the server. Both conditions must be breached together before an exception is
          raised, so a large percentage on a trivial amount is not worth anyone time.
        </p>
      </div>
    </div>
  );
}
