import './Footer.css';

const MARK = import.meta.env.BASE_URL + 'lyftbridge-favicon.png';

export function Footer({ className = '' }) {
  return (
    <footer className={`lb-footer ${className}`}>
      <img src={MARK} alt="" aria-hidden="true" className="lb-footer__mark" />
      <span className="lb-footer__copy">© 2026 Lyftbridge Innovation LLC</span>
    </footer>
  );
}
