import { useEffect, useRef, useState } from 'react';
import Script from 'next/script';

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '';

export default function GoogleSignInButton({
  onCredential,
  disabled = false,
  text = 'signin_with',
}) {
  const containerRef = useRef(null);
  const [scriptReady, setScriptReady] = useState(false);

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || !scriptReady || !containerRef.current || !window.google?.accounts?.id) {
      return;
    }

    containerRef.current.innerHTML = '';
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: async ({ credential }) => {
        if (!credential || disabled) return;
        await onCredential(credential);
      },
      auto_select: false,
      cancel_on_tap_outside: true,
    });

    window.google.accounts.id.renderButton(containerRef.current, {
      type: 'standard',
      theme: 'outline',
      size: 'large',
      shape: 'pill',
      text,
      width: 360,
      logo_alignment: 'left',
    });
  }, [disabled, onCredential, scriptReady, text]);

  if (!GOOGLE_CLIENT_ID) {
    return null;
  }

  return (
    <>
      <Script
        src="https://accounts.google.com/gsi/client"
        strategy="afterInteractive"
        onLoad={() => setScriptReady(true)}
      />
      <div className={disabled ? 'opacity-50 pointer-events-none' : ''}>
        <div ref={containerRef} />
      </div>
    </>
  );
}
