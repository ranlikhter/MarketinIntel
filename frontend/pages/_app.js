import '../styles/globals.css';
import { ToastProvider } from '../components/Toast';
import { AuthProvider } from '../context/AuthContext';
import { PwaProvider } from '../context/PwaContext';

function MyApp({ Component, pageProps }) {
  return (
    <AuthProvider>
      <ToastProvider>
        <PwaProvider>
          <Component {...pageProps} />
        </PwaProvider>
      </ToastProvider>
    </AuthProvider>
  );
}

export default MyApp;
