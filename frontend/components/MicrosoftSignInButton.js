export default function MicrosoftSignInButton({
  onClick,
  disabled = false,
  label = 'Continue with Microsoft',
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="w-full inline-flex items-center justify-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      style={{ background: '#2563eb', color: '#ffffff' }}
    >
      <svg className="w-5 h-5" viewBox="0 0 23 23" fill="none" aria-hidden="true">
        <path d="M1 1h10v10H1V1Z" fill="#f25022" />
        <path d="M12 1h10v10H12V1Z" fill="#7fba00" />
        <path d="M1 12h10v10H1V12Z" fill="#00a4ef" />
        <path d="M12 12h10v10H12V12Z" fill="#ffb900" />
      </svg>
      <span>{label}</span>
    </button>
  );
}
