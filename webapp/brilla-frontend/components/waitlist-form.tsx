"use client";
import { useState } from "react";

const WaitlistForm = () => {
  const [email, setEmail] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    alert(`Email ${email} submitted!`);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h2 className="text-2xl font-bold text-center text-purple-700">
        Join the waitlist
      </h2>
      <p className="text-center text-gray-600">
        Enter your email and submit to get notifications when Brilla AI goes
        live ✨
      </p>
      <input
        type="email"
        placeholder="Enter your email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        className="w-full border border-gray-300 rounded-lg p-2 focus:outline-none focus:border-purple-600"
        required
      />
      <button
        type="submit"
        className="w-full bg-gradient-to-r from-purple-600 via-purple-800 to-indigo-500 text-white py-2 rounded-lg hover:bg-bg-gradient-to-l hover:from-purple-700 hover:via-purple-900/100 hover:to-indigo-600"
      >
        Submit
      </button>
    </form>
  );
};

export default WaitlistForm;
