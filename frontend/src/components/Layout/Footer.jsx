import './Footer.css';

const LOGO = import.meta.env.BASE_URL + 'lyftbridge.jpeg';

export function Footer({ className = '' }) {
  return (
    <footer className={`lb-footer ${className}`}>
      <img src={LOGO} alt="Lyftbridge" className="lb-footer__logo" />
      <span className="lb-footer__copy">© 2026 Lyftbridge. All rights reserved.</span>
    </footer>
  );
}
