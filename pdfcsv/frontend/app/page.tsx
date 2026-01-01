'use client';

import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="container mx-auto px-4 py-6">
        <nav className="flex justify-between items-center">
          <div className="text-2xl font-bold text-blue-600">
            FinFlow AI
          </div>
          <div className="space-x-4">
            <Link 
              href="/login"
              className="px-4 py-2 text-gray-700 hover:text-gray-900"
            >
              Log In
            </Link>
            <Link
              href="/signup"
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              Sign Up
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <main className="container mx-auto px-4 py-20">
        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
            Stop Manually Importing
            <span className="block text-blue-600 mt-2">Bank Statements</span>
          </h1>
          
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            Upload PDF → Review Transactions → Sync to QuickBooks
            <br />
            <span className="font-semibold">Done in 30 seconds.</span>
          </p>

          <div className="flex gap-4 justify-center mb-12">
            <Link
              href="/signup"
              className="px-8 py-4 bg-blue-600 text-white text-lg rounded-lg hover:bg-blue-700 transition shadow-lg"
            >
              Start Free Trial
            </Link>
            <Link
              href="#how-it-works"
              className="px-8 py-4 bg-white text-gray-700 text-lg rounded-lg hover:bg-gray-50 transition shadow-lg"
            >
              See How It Works
            </Link>
          </div>

          <p className="text-sm text-gray-500">
            Free tier: 100 pages/month • No credit card required
          </p>
        </div>

        {/* Features */}
        <div id="how-it-works" className="mt-32 grid md:grid-cols-3 gap-8">
          <div className="bg-white p-8 rounded-xl shadow-lg">
            <div className="text-4xl mb-4">📄</div>
            <h3 className="text-xl font-bold mb-2">Upload PDF</h3>
            <p className="text-gray-600">
              Drag and drop your bank statement. We support all major banks.
            </p>
          </div>

          <div className="bg-white p-8 rounded-xl shadow-lg">
            <div className="text-4xl mb-4">🤖</div>
            <h3 className="text-xl font-bold mb-2">AI Extraction</h3>
            <p className="text-gray-600">
              GPT-4 extracts and categorizes transactions with 95%+ accuracy.
            </p>
          </div>

          <div className="bg-white p-8 rounded-xl shadow-lg">
            <div className="text-4xl mb-4">✅</div>
            <h3 className="text-xl font-bold mb-2">Sync to QuickBooks</h3>
            <p className="text-gray-600">
              One-click sync. No CSV downloads. No manual imports.
            </p>
          </div>
        </div>

        {/* Comparison */}
        <div className="mt-32 max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12">
            Why Choose FinFlow AI?
          </h2>
          
          <div className="bg-white rounded-xl shadow-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-4 text-left"></th>
                  <th className="px-6 py-4 text-center text-blue-600">FinFlow AI</th>
                  <th className="px-6 py-4 text-center text-gray-500">Others</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                <tr>
                  <td className="px-6 py-4 font-medium">Direct QuickBooks Sync</td>
                  <td className="px-6 py-4 text-center text-green-600 text-xl">✓</td>
                  <td className="px-6 py-4 text-center text-red-600 text-xl">✗</td>
                </tr>
                <tr>
                  <td className="px-6 py-4 font-medium">AI-Powered Categorization</td>
                  <td className="px-6 py-4 text-center text-green-600 text-xl">✓</td>
                  <td className="px-6 py-4 text-center text-yellow-600 text-xl">~</td>
                </tr>
                <tr>
                  <td className="px-6 py-4 font-medium">Real-Time Processing</td>
                  <td className="px-6 py-4 text-center text-green-600 text-xl">✓</td>
                  <td className="px-6 py-4 text-center text-red-600 text-xl">✗</td>
                </tr>
                <tr>
                  <td className="px-6 py-4 font-medium">Price (Professional)</td>
                  <td className="px-6 py-4 text-center font-bold">$69/mo</td>
                  <td className="px-6 py-4 text-center text-gray-500">$111/mo</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Pricing */}
        <div className="mt-32 max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12">
            Simple, Transparent Pricing
          </h2>
          
          <div className="grid md:grid-cols-2 gap-8">
            {/* Free Tier */}
            <div className="bg-white rounded-xl shadow-lg p-8">
              <h3 className="text-2xl font-bold mb-2">Free</h3>
              <div className="text-4xl font-bold mb-4">$0<span className="text-lg text-gray-500">/month</span></div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-center">
                  <span className="text-green-600 mr-2">✓</span>
                  100 pages per month
                </li>
                <li className="flex items-center">
                  <span className="text-green-600 mr-2">✓</span>
                  Bank statements only
                </li>
                <li className="flex items-center">
                  <span className="text-green-600 mr-2">✓</span>
                  QuickBooks sync
                </li>
                <li className="flex items-center">
                  <span className="text-green-600 mr-2">✓</span>
                  Email support
                </li>
              </ul>
              <Link
                href="/signup"
                className="block w-full text-center px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
              >
                Get Started
              </Link>
            </div>

            {/* Pro Tier */}
            <div className="bg-blue-600 text-white rounded-xl shadow-lg p-8 relative">
              <div className="absolute top-0 right-0 bg-yellow-400 text-blue-900 px-4 py-1 rounded-bl-lg rounded-tr-xl font-bold text-sm">
                POPULAR
              </div>
              <h3 className="text-2xl font-bold mb-2">Professional</h3>
              <div className="text-4xl font-bold mb-4">$69<span className="text-lg opacity-80">/month</span></div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-center">
                  <span className="mr-2">✓</span>
                  7,500 pages per year
                </li>
                <li className="flex items-center">
                  <span className="mr-2">✓</span>
                  All document types
                </li>
                <li className="flex items-center">
                  <span className="mr-2">✓</span>
                  QuickBooks sync
                </li>
                <li className="flex items-center">
                  <span className="mr-2">✓</span>
                  AI categorization
                </li>
                <li className="flex items-center">
                  <span className="mr-2">✓</span>
                  Priority support
                </li>
              </ul>
              <Link
                href="/signup"
                className="block w-full text-center px-6 py-3 bg-white text-blue-600 rounded-lg hover:bg-gray-100 transition font-semibold"
              >
                Start Free Trial
              </Link>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="mt-32 text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to save 18 hours per month?</h2>
          <p className="text-xl text-gray-600 mb-8">
            Join bookkeepers who've automated their workflow
          </p>
          <Link
            href="/signup"
            className="inline-block px-8 py-4 bg-blue-600 text-white text-lg rounded-lg hover:bg-blue-700 transition shadow-lg"
          >
            Start Free Trial →
          </Link>
        </div>
      </main>

      {/* Footer */}
      <footer className="container mx-auto px-4 py-8 mt-32 border-t border-gray-300">
        <div className="text-center text-gray-600">
          <p>&copy; 2026 FinFlow AI. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
