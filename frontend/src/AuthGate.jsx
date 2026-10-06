import { createContext, useContext, useEffect, useState } from "react";
import { supabase, supabaseConfigured } from "./supabase";

const AuthContext = createContext({ user: null, signOut: async () => {} });
export const useAuth = () => useContext(AuthContext);

export default function AuthGate({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  const [mode, setMode] = useState("login");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const isReset = window.location.pathname === "/reset-password";

  useEffect(() => {
    if (!supabase) {
      setError("Supabase is not configured. Add the project URL and publishable key to the local .env file.");
      setReady(true);
      return;
    }
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user || null);
    });
    supabase.auth.getSession()
      .then(({ data, error: sessionError }) => {
        if (sessionError) throw sessionError;
        setUser(data.session?.user || null);
      })
      .catch(exception => setError(exception.message || "Could not load your Supabase session."))
      .finally(() => setReady(true));
    return () => subscription.unsubscribe();
  }, []);

  async function submit(event) {
    event.preventDefault(); setError(""); setNotice(""); setBusy(true);
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") || "").trim();
    const password = String(form.get("password") || "");
    if (mode === "register" && password !== String(form.get("password_confirm") || "")) {
      setError("The passwords do not match."); setBusy(false); return;
    }
    try {
      if (mode === "register") {
        const { data, error: authError } = await supabase.auth.signUp({
          email, password,
          options: { data: { full_name: email.split("@")[0] }, emailRedirectTo: window.location.origin },
        });
        if (authError) throw authError;
        if (data.session) setUser(data.user);
        else setNotice("Check your email for a confirmation link before signing in.");
      } else {
        const { data, error: authError } = await supabase.auth.signInWithPassword({ email, password });
        if (authError) throw authError;
        setUser(data.user);
      }
    } catch (exception) { setError(exception.message || "Could not sign in."); }
    finally { setBusy(false); }
  }

  async function sendReset(event) {
    event.preventDefault(); setError(""); setNotice(""); setBusy(true);
    try {
      const email = String(new FormData(event.currentTarget).get("email") || "").trim();
      const { error: authError } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
      });
      if (authError) throw authError;
      setNotice("If an account exists for that email, Supabase has sent a password reset link.");
    } catch (exception) { setError(exception.message || "Could not request a password reset."); }
    finally { setBusy(false); }
  }

  async function resetPassword(event) {
    event.preventDefault(); setError(""); setBusy(true);
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") || "");
    const confirm = String(form.get("password_confirm") || "");
    if (password !== confirm) { setError("The passwords do not match."); setBusy(false); return; }
    try {
      const { error: authError } = await supabase.auth.updateUser({ password });
      if (authError) throw authError;
      await supabase.auth.signOut();
      window.history.replaceState({}, "", "/");
      setMode("login");
      setNotice("Your password has been updated. You can now sign in.");
    } catch (exception) { setError(exception.message || "Could not reset your password."); }
    finally { setBusy(false); }
  }

  async function signInWithGoogle() {
    setError(""); setBusy(true);
    const { error: authError } = await supabase.auth.signInWithOAuth({
      provider: "google", options: { redirectTo: window.location.origin },
    });
    if (authError) { setError(authError.message); setBusy(false); }
  }

  async function signOut() {
    const { error: authError } = await supabase.auth.signOut();
    if (authError) throw authError;
    setUser(null);
  }

  if (!ready) return <main className="auth-screen"><div className="auth-card"><span className="auth-mark">✦</span><p>Waking up your garden…</p></div></main>;
  if (user && !isReset) return <AuthContext.Provider value={{ user, signOut }}>{children}</AuthContext.Provider>;

  return <main className="auth-screen"><section className="auth-card">
    <div className="auth-brand"><span className="auth-mark">✦</span><div><span className="brand-kicker">YOUR LITTLE PATCH IN SPACE</span><h1>SpaceFruit</h1></div></div>
    <p className="eyebrow">A GARDEN THAT GROWS WITH YOU</p>
    <h2>{isReset ? "Choose a new password" : mode === "register" ? "Start your garden" : mode === "forgot" ? "Find your way back" : "Welcome back, grower"}</h2>
    <p className="auth-description">{isReset ? "Set a fresh password for your SpaceFruit account." : "Sign in to tend your plants and share with your growing community."}</p>
    {error && <div className="error" role="alert">{error}</div>}{notice && <div className="auth-notice" role="status">{notice}</div>}
    {isReset ? <form onSubmit={resetPassword} className="auth-form"><label>New password<input required minLength="8" type="password" name="password" autoComplete="new-password"/></label><label>Confirm new password<input required minLength="8" type="password" name="password_confirm" autoComplete="new-password"/></label><button className="primary-button" disabled={busy || !user}>Save new password</button>{!user && <small>Open this page using the password reset link from your email.</small>}</form> : mode === "forgot" ? <form onSubmit={sendReset} className="auth-form"><label>Email address<input required type="email" name="email" autoComplete="email"/></label><button className="primary-button" disabled={busy}>Send reset link</button></form> : <>
      <button className="google-button" type="button" disabled={busy} onClick={signInWithGoogle}><b>G</b> Continue with Google</button><div className="auth-divider"><span>or with email</span></div>
      <form onSubmit={submit} className="auth-form"><label>Email address<input required type="email" name="email" autoComplete="email"/></label><label>Password<input required minLength={mode === "register" ? 8 : undefined} type="password" name="password" autoComplete={mode === "register" ? "new-password" : "current-password"}/></label>{mode === "register"&&<label>Confirm password<input required minLength="8" type="password" name="password_confirm" autoComplete="new-password"/></label>}<button className="primary-button" disabled={busy || !supabaseConfigured}>{mode === "register" ? "Create account" : "Sign in"}</button></form>
      {mode === "login" && <button className="auth-text-button" onClick={()=>{setMode("forgot");setError("");setNotice("");}}>Forgot your password?</button>}
      <p className="auth-switch">{mode === "register" ? "Already have an account?" : "New to SpaceFruit?"} <button onClick={()=>{setMode(mode === "register" ? "login" : "register");setError("");setNotice("");}}>{mode === "register" ? "Sign in" : "Create an account"}</button></p>
    </>}
    {(mode === "forgot" || isReset) && <p className="auth-switch"><button onClick={()=>{window.history.replaceState({}, "", "/");setMode("login");setError("");setNotice("");}}>Back to sign in</button></p>}
    <small className="auth-footnote">A cozy home for your plants, robot, and growing community.</small>
  </section></main>;
}
