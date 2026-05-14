import { styled } from '@mui/material/styles';
import { keyframes } from '@emotion/react';
import { Button, Typography } from '@mui/material';

const fadeIn = keyframes`
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
`;

const fadeInUp = keyframes`
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
`;

const buttonPulse = keyframes`
  0% { box-shadow: 0 0 0 0 rgba(74, 246, 38, 0.15); }
  70% { box-shadow: 0 0 0 8px rgba(74, 246, 38, 0); }
  100% { box-shadow: 0 0 0 0 rgba(74, 246, 38, 0); }
`;

const float = keyframes`
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-10px) rotate(2deg); }
`;

const vanish = keyframes`
  from { opacity: 1; transform: translateY(0); }
  to { opacity: 0; transform: translateY(-20px); }
`;

const appear = keyframes`
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
`;

const ghostHit = keyframes`
  0% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-15px) scale(1.1); }
  100% { transform: translateY(0) scale(1); }
`;

const particleFloat = keyframes`
  0% { transform: translateY(0) rotate(0deg); opacity: 0; }
  50% { opacity: 0.2; }
  100% { transform: translateY(-15px) rotate(180deg); opacity: 0; }
`;

const transitionFade = keyframes`
  0% { opacity: 0; }
  100% { opacity: 1; }
`;

const dotsFlashing = keyframes`
  0% { content: '.'; }
  33% { content: '..'; }
  66% { content: '...'; }
  100% { content: '.'; }
`;

const pulseGlow = keyframes`
  0% { filter: drop-shadow(0 0 8px rgba(74, 246, 38, 0.3)); }
  50% { filter: drop-shadow(0 0 12px rgba(74, 246, 38, 0.5)); }
  100% { filter: drop-shadow(0 0 8px rgba(74, 246, 38, 0.3)); }
`;

export { fadeIn };

export const ConfigContainer = styled('div')({ maxWidth: 1200, margin: '0 auto', padding: '0 24px' });

export const HeroSection = styled('div')({
  minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
  textAlign: 'center', background: '#000',
});

export const HeroContent = styled('div')({
  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '32px',
  maxWidth: '800px', margin: '0 auto', padding: '40px 20px',
  animation: `${fadeIn} 0.8s ease-out`,
});

export const LogoImage = styled('img')({
  width: '140px', height: '140px', marginBottom: '24px',
  transition: 'all 0.3s ease',
  filter: 'drop-shadow(0 0 8px rgba(74, 246, 38, 0.3))',
  '&.floating': { animation: `${float} 2s ease-in-out infinite` },
  '&.hitting': { animation: `${ghostHit} 0.5s ease-out` },
});

export const WordmarkContainer = styled('div')({
  display: 'flex', justifyContent: 'center', alignItems: 'center',
  width: '100%', marginBottom: '24px', position: 'relative', zIndex: 1,
  '& span': {
    display: 'inline-block', fontSize: '72px', fontWeight: 400, color: '#FFFFFF',
    margin: '0 8px', willChange: 'transform, opacity, filter',
    transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
    textShadow: '0 0 5px rgba(74, 246, 38, 0.2), 0 0 10px rgba(74, 246, 38, 0.25), 0 0 15px rgba(74, 246, 38, 0.2)',
  },
  '&.vanishing span': {
    animation: `${vanish} 0.6s cubic-bezier(0.4, 0, 0.2, 1) forwards`,
    animationDelay: 'calc(var(--char-index) * 0.03s)',
  },
  '&.appearing span': {
    animation: `${appear} 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards`,
    animationDelay: 'calc(var(--char-index) * 0.03s)',
  },
});

export const HeroTitle = styled(Typography)({
  fontSize: '32px', fontWeight: 500, color: '#EDEDED', marginBottom: '24px',
  textAlign: 'center', textTransform: 'lowercase', lineHeight: '1.4',
  opacity: 0, animation: `${fadeInUp} 0.8s ease-out 0.6s forwards`,
});

export const HeroSubtitle = styled(Typography)({
  fontSize: '20px', color: '#AAAAAA', marginBottom: '40px',
  textAlign: 'center', textTransform: 'lowercase', lineHeight: '1.6',
  letterSpacing: '0.5px', fontWeight: 400,
  opacity: 0, animation: `${fadeInUp} 0.8s ease-out 0.8s forwards`,
});

export const ConfigSection = styled('div')`
  max-width: 800px; margin: 0 auto; padding: 2rem;
  animation: ${fadeIn} 0.3s ease-out;
`;

export const Separator = styled('div')({
  display: 'flex', alignItems: 'center', margin: '40px 0',
  color: 'rgba(255, 255, 255, 0.5)', fontSize: '14px',
  '&::before, &::after': { content: '""', flex: 1, borderBottom: '1px solid rgba(255, 255, 255, 0.1)' },
  '&::before': { marginRight: '16px' },
  '&::after': { marginLeft: '16px' },
});

export const ArnInput = styled('div')`
  display: flex; align-items: center; margin: 40px 0;
  input, select {
    background: transparent; border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
    color: #fff; font-size: 18px; padding: 8px 0; width: 100%; text-align: left;
    &:focus { outline: none; box-shadow: 0 0 0 2px rgba(74, 246, 38, 0.2); border-bottom-color: #4AF626; }
    &::placeholder { color: rgba(255, 255, 255, 0.3); }
  }
  select {
    color: #fff; appearance: none;
    background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ffffff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
    background-repeat: no-repeat; background-position: right 0px center; background-size: 16px;
    padding-right: 20px;
  }
  select option { background-color: #121212; color: #fff; }
`;

const actionButtonBase = `
  background: #000; color: #fff; padding: 16px 32px; font-size: 18px;
  font-weight: 500; border-radius: 8px; text-transform: lowercase; width: 100%;
  margin: 40px 0; position: relative; overflow: hidden; transition: all 0.3s ease;
  animation: ${buttonPulse} 2s infinite; border: 1px solid rgba(74, 246, 38, 0.3);
  &:hover { background: #222; transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3); }
`;

export const ConnectButton = styled(Button)`${actionButtonBase}`;
export const DeployRoleButton = styled(Button)`${actionButtonBase}`;

export const DeployButton = styled(Button)({
  background: '#000', color: '#fff', padding: '16px 32px', fontSize: '18px',
  fontWeight: 500, borderRadius: '8px', textTransform: 'lowercase',
  marginTop: '24px', position: 'relative', overflow: 'hidden', transition: 'all 0.3s ease',
  opacity: 0, border: '1px solid rgba(74, 246, 38, 0.3)',
  animation: `${fadeInUp} 0.8s ease-out 1s forwards, ${buttonPulse} 2s 1.8s infinite`,
  '&:hover': {
    background: '#222', transform: 'translateY(-2px)', boxShadow: '0 5px 15px rgba(0, 0, 0, 0.3)',
    '& .button-icon': { transform: 'translateX(5px)' },
  },
  '& .button-icon': { marginLeft: '8px', transition: 'transform 0.3s ease' },
});

export const GhostedMessage = styled(Typography)({
  fontSize: '20px', color: '#888888', marginTop: '16px', marginBottom: '32px',
  opacity: 0, transform: 'translateY(10px)',
  transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)', textTransform: 'lowercase',
  '&.visible': { opacity: 1, transform: 'translateY(0)' },
});

export const Particle = styled('div')({
  position: 'absolute', width: '2px', height: '2px',
  background: 'rgba(255, 255, 255, 0.3)', borderRadius: '50%',
  animation: `${particleFloat} 3s ease-in-out infinite`,
  animationDelay: 'calc(var(--particle-index) * 0.2s)',
});

export const ParticleContainer = styled('div')({
  position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
  overflow: 'hidden', pointerEvents: 'none',
});

export const PageTransition = styled('div')({
  position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
  background: '#000000', zIndex: 9999, opacity: 0, pointerEvents: 'none',
  display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center',
  transition: 'opacity 0.5s ease',
  '&.active': { opacity: 1, pointerEvents: 'all', animation: `${transitionFade} 0.5s ease` },
});

export const GhostLogo = styled('div')<{ bgUrl: string }>(({ bgUrl }) => ({
  width: '64px', height: '64px',
  background: `url(${bgUrl})`, backgroundSize: 'contain',
  backgroundRepeat: 'no-repeat', backgroundPosition: 'center',
  marginBottom: '24px', animation: `${pulseGlow} 2s infinite ease-in-out`, opacity: 0.9,
}));

export const ConnectingText = styled('div')({
  fontFamily: '"Fira Code", monospace', fontSize: '16px', color: '#ffffff',
  letterSpacing: '0.5px', position: 'relative',
  textShadow: '0 0 8px rgba(74, 246, 38, 0.3)',
  '&::after': {
    content: '"."', position: 'absolute',
    animation: `${dotsFlashing} 1.5s infinite steps(1, end)`, marginLeft: '2px',
  },
});
