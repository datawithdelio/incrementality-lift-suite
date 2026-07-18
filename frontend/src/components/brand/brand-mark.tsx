type BrandMarkProps = {
  compact?: boolean;
  inverted?: boolean;
};

export function BrandMark({ compact = false, inverted = false }: BrandMarkProps) {
  return (
    <span className={`brand-lockup${compact ? " brand-lockup-compact" : ""}${inverted ? " brand-lockup-inverted" : ""}`}>
      <span className="brand-glyph" aria-hidden="true">
        <i />
        <i />
        <i />
      </span>
      {!compact && <span>Incrementality</span>}
    </span>
  );
}
