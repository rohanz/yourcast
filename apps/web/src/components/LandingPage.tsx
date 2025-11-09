'use client'

import { useAuth } from '@/contexts/AuthContext'
import { useState, useEffect } from 'react'

export function LandingPage() {
  const { signInWithGoogle, user } = useAuth()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fadeOut, setFadeOut] = useState(false)

  // Fade out when user is authenticated
  useEffect(() => {
    if (user) {
      setFadeOut(true)
    }
  }, [user])

  const handleSignIn = async () => {
    try {
      setLoading(true)
      setError(null)
      await signInWithGoogle()
      // Fade out will happen via useEffect when user state updates
    } catch (err) {
      setError('Failed to sign in with Google. Please try again.')
      console.error(err)
      setLoading(false)
    }
  }

  return (
    <div className={`h-screen bg-white flex flex-col transition-opacity duration-500 ${fadeOut ? 'opacity-0' : 'opacity-100 animate-fadeIn'}`} style={{ paddingLeft: '2vw', paddingRight: '2vw', paddingTop: '6vh', overflow: 'hidden' }}>
      <div className="w-full mx-auto flex flex-col items-center" style={{ maxWidth: '95vw' }}>

        {/* Hero Section - Compact */}
        <div className="text-center" style={{ marginBottom: 'min(0.2vh, 0.15rem)' }}>
          <h1 className="font-bold lowercase" style={{ fontSize: 'clamp(1.8rem, 4vw + 0.8vh, 4.5rem)', lineHeight: '1.1' }}>
            <span className="bg-gradient-to-r from-red-400 to-red-500 bg-clip-text text-transparent">your</span>
            <span className="bg-gradient-to-r from-maroon-900 to-maroon-700 bg-clip-text text-transparent">cast!</span>
          </h1>
          <p className="text-maroon-800 font-light" style={{ fontSize: 'clamp(0.85rem, 1.5vw + 0.4vh, 1.6rem)', marginTop: 'min(1.8vh, 0.9rem)' }}>your daily brief, without the noise.</p>
          <p className="text-tan-600 font-normal mx-auto leading-tight" style={{ fontSize: 'clamp(0.75rem, 1.3vw + 0.3vh, 1.15rem)', marginTop: 'min(0.4vh, 0.25rem)', maxWidth: '80vw', paddingLeft: '1vw', paddingRight: '1vw' }}>
            tell us what you're into, and we'll make you a fresh, personalized podcast daily.
          </p>
          <p className="font-bold text-maroon-800 mx-auto" style={{ fontSize: 'clamp(0.75rem, 1.3vw + 0.3vh, 1.15rem)', marginTop: 'min(1.8vh, 0.9rem)', maxWidth: '80vw' }}>
            for free.
          </p>
        </div>

        {/* Rotating Rings with CTA - Dominant Visual */}
        <div className="relative flex items-center justify-center" style={{ overflow: 'visible', width: '100%' }}>
          <div className="relative" style={{ width: 'clamp(450px, min(110vw, 85vh), 900px)', overflow: 'visible' }}>
            {/* SVG Graphic */}
            <div className="relative w-full pb-[80%]">
              <svg id="topicsSvg" viewBox="0 0 600 500" className="absolute inset-0 w-full h-full" role="img" aria-label="Rotating topic rings" style={{ overflow: 'visible' }}>
              <defs>
                <linearGradient id="fadeGradient" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="500" gradientTransform="rotate(0, 300, 250)">
                  <stop offset="0%" stopColor="white"/>
                  <stop offset="44%" stopColor="white"/>
                  <stop offset="48%" stopColor="#e6e6e6"/>
                  <stop offset="50%" stopColor="#999999"/>
                  <stop offset="52%" stopColor="#000000"/>
                  <stop offset="100%" stopColor="black"/>
                </linearGradient>

                <path id="path-outer" d="M300,250 m-185,0 a185,185 0 1,1 370,0 a185,185 0 1,1 -370,0" />
                <path id="path-second" d="M300,250 m-155,0 a155,155 0 1,1 310,0 a155,155 0 1,1 -310,0" />
                <path id="path-middle" d="M300,250 m-125,0 a125,125 0 1,1 250,0 a125,125 0 1,1 -250,0" />
                <path id="path-fourth" d="M300,250 m-95,0 a95,95 0 1,1 190,0 a95,95 0 1,1 -190,0" />
                <path id="path-inner" d="M300,250 m-65,0 a65,65 0 1,1 130,0 a65,65 0 1,1 -130,0" />

                <mask id="mask-outer"><g className="rotate-outer-counter"><rect width="600" height="500" fill="url(#fadeGradient)" /></g></mask>
                <mask id="mask-second"><g className="rotate-second-counter"><rect width="600" height="500" fill="url(#fadeGradient)" /></g></mask>
                <mask id="mask-middle"><g className="rotate-middle-counter"><rect width="600" height="500" fill="url(#fadeGradient)" /></g></mask>
                <mask id="mask-fourth"><g className="rotate-fourth-counter"><rect width="600" height="500" fill="url(#fadeGradient)" /></g></mask>
                <mask id="mask-inner"><g className="rotate-inner-counter"><rect width="600" height="500" fill="url(#fadeGradient)" /></g></mask>
              </defs>

              <g className="rotate-outer" mask="url(#mask-outer)">
                <text className="ring-text" fontSize="12" fill="rgba(107, 87, 68, 0.75)" style={{ opacity: 0.55 }}>
                  <textPath href="#path-outer" textLength="1162" lengthAdjust="spacingAndGlyphs">{'\n'}
                  {'                  '}<tspan fill="#8b7355">world news</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">us politics</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#8b7355">international politics</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">elections</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#8b7355">policy & legislation</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">government affairs</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">corporations & earnings</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#8b7355">startups & entrepreneurship</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">economy and policy</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#8b7355">global economy</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">business and finance</tspan>&nbsp;{'\n'}
                {'                '}</textPath>
                </text>
              </g>

              <g className="rotate-second" mask="url(#mask-second)">
                <text className="ring-text" fontSize="12" fill="rgba(107, 87, 68, 0.75)" style={{ opacity: 0.60 }}>
                  <textPath href="#path-second" textLength="974" lengthAdjust="spacingAndGlyphs">{'\n'}
                  {'                  '}<tspan fill="#8b7355">gadgets & consumer tech</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">software & apps</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#8b7355">space & astronomy</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">biology</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#8b7355">physics & chemistry</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">basketball</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#8b7355">cybersecurity</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">hardware & infrastructure</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#8b7355">ai & machine learning</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">data science</tspan>&nbsp;{'\n'}
                {'                '}</textPath>
                </text>
              </g>

              <g className="rotate-middle" mask="url(#mask-middle)">
                <text className="ring-text" fontSize="12" fill="rgba(107, 87, 68, 0.75)" style={{ opacity: 0.65 }}>
                  <textPath href="#path-middle" textLength="785" lengthAdjust="spacingAndGlyphs">{'\n'}
                  {'                  '}<tspan fill="#8b7355">research & academia</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">climate & weather</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#8b7355">sustainability</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">conservation & wildlife</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#8b7355">football (soccer)</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">american football</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#8b7355">baseball</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#8b7355">tennis</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">elections</tspan>&nbsp;{'\n'}
                {'                '}</textPath>
                </text>
              </g>

              <g className="rotate-fourth" mask="url(#mask-fourth)">
                <text className="ring-text" fontSize="12" fill="rgba(107, 87, 68, 0.75)" style={{ opacity: 0.70 }}>
                  <textPath href="#path-fourth" textLength="597" lengthAdjust="spacingAndGlyphs">{'\n'}
                  {'                  '}<tspan fill="#8b7355">boxing</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">mma</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#8b7355">golf</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">ice hockey</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#8b7355">tennis</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">volleyball</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#8b7355">table tennis (ping pong)</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">athletics</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#8b7355">art and design</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">travel</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#8b7355">hobbies</tspan>&nbsp;{'\n'}
                {'                '}</textPath>
                </text>
              </g>

              <g className="rotate-inner" mask="url(#mask-inner)">
                <text className="ring-text" fontSize="12" fill="rgba(107, 87, 68, 0.75)" style={{ opacity: 0.75 }}>
                  <textPath href="#path-inner" textLength="408" lengthAdjust="spacingAndGlyphs">{'\n'}
                  {'                  '}<tspan fill="#8b7355">gaming</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">film & tv</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#8b7355">music</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">literature</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#8b7355">art & design</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">fashion</tspan>&nbsp;{'\n'}
                  {'                  '}<tspan fill="#4a1010">food & dining</tspan>&nbsp;{'\n'}
                {'                '}</textPath>
                </text>
              </g>

              {/* Waveform */}
              <g transform="translate(300, 255) scale(0.5) rotate(180)">
                <rect x="-54" y="0" width="10" rx="2" className="wave-1" fill="#7f1d1d" opacity="0.9"/>
                <rect x="-36" y="0" width="10" rx="2" className="wave-2" fill="#7f1d1d" opacity="0.9"/>
                <rect x="-18" y="0" width="10" rx="2" className="wave-3" fill="#7f1d1d" opacity="0.9"/>
                <rect x="0" y="0" width="10" rx="2" className="wave-4" fill="#7f1d1d" opacity="0.9"/>
                <rect x="18" y="0" width="10" rx="2" className="wave-5" fill="#7f1d1d" opacity="0.9"/>
                <rect x="36" y="0" width="10" rx="2" className="wave-6" fill="#7f1d1d" opacity="0.9"/>
                <rect x="54" y="0" width="10" rx="2" className="wave-7" fill="#7f1d1d" opacity="0.9"/>
              </g>
              </svg>
            </div>

            {/* CTA positioned in center of graphic */}
            <div className="absolute left-1/2 -translate-x-1/2 -translate-y-1/2 text-center w-full z-10" style={{ top: '70%' }}>
              <button
                onClick={handleSignIn}
                disabled={loading}
                className="bg-gradient-to-r from-red-400 to-red-500 text-white font-semibold transition-transform transform hover:scale-105 lowercase disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
                style={{
                  fontSize: 'clamp(1.1rem, 1.5vw + 0.3vh, 1.25rem)',
                  padding: 'clamp(0.75rem, 1vh + 0.2vw, 1rem) clamp(2rem, 3vw + 0.5vh, 3rem)',
                  borderRadius: 'clamp(0.5rem, 1vw + 0.2vh, 1rem)'
                }}
              >
                {loading ? 'signing in...' : 'start listening now →'}
              </button>
              <p className="text-tan-600" style={{ fontSize: 'clamp(0.8rem, 1.2vw + 0.2vh, 0.875rem)', marginTop: 'min(0.8vh, 0.4rem)' }}>sign in with Google to get started</p>
              {error && (
                <p className="text-red-600" style={{ fontSize: 'clamp(0.7rem, 1.2vw + 0.2vh, 0.875rem)', marginTop: 'min(0.8vh, 0.4rem)' }}>{error}</p>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
