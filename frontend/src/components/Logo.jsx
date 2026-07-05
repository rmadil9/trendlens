export default function Logo({ size = 26 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="brand-logo"
      aria-hidden="true"
    >
      <circle cx="13" cy="13" r="8" stroke="currentColor" strokeWidth="2.5" />
      <path
        d="M9 15l3-4.5 2.5 2.5L18.5 8"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <line
        x1="18.8"
        y1="18.8"
        x2="27"
        y2="27"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  );
}
