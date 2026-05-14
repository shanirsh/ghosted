import { styled, keyframes } from '@mui/material/styles';
import { Container, Typography, Box, IconButton, Button, Paper, Chip } from '@mui/material';

const shimmer = keyframes`
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
`;

const slideIn = keyframes`
  0% { transform: translateY(-20px); opacity: 0; }
  100% { transform: translateY(0); opacity: 1; }
`;

const fadeIn = keyframes`
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
`;

const rippleEffect = keyframes`
  0% { transform: scale(0); opacity: 1; }
  100% { transform: scale(2.5); opacity: 0; }
`;

const slideRight = keyframes`
  0% { transform: translateX(0); }
  100% { transform: translateX(5px); }
`;

export const PageContainer = styled(Container)({
  padding: '2rem',
  backgroundColor: '#0A0A0A',
  minHeight: '100vh',
  color: '#FFFFFF',
  width: '100%',
  position: 'relative',
  zIndex: 1000,
  animation: `${fadeIn} 0.3s ease-out`,
  overflowY: 'auto',
  maxHeight: '100vh',
  '&::-webkit-scrollbar': { display: 'none' },
  msOverflowStyle: 'none',
  scrollbarWidth: 'none',
});

export const PageHeader = styled(Box)({
  display: 'flex',
  alignItems: 'center',
  marginBottom: '2rem',
  position: 'relative',
  paddingLeft: '0',
  height: '50px',
});

export const PageTitle = styled(Typography)({
  color: '#FFFFFF',
  fontWeight: 'bold',
  fontSize: '2.2rem',
  letterSpacing: '8px',
  marginLeft: '1rem',
  fontFamily: "'Söhne Mono', monospace",
  textShadow: '0 0 15px rgba(0, 255, 127, 0.7)',
  textTransform: 'uppercase',
});

export const DeploymentCard = styled(Paper)({
  backgroundColor: '#111111',
  borderRadius: '8px',
  padding: '1.2rem',
  marginBottom: '1.8rem',
  boxShadow: '0 8px 16px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(0, 255, 127, 0.1)',
  border: '1px solid rgba(0, 255, 127, 0.1)',
  transition: 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
  position: 'relative',
  overflow: 'hidden',
  '&:hover': {
    transform: 'translateY(-5px)',
    boxShadow: '0 12px 24px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(0, 255, 127, 0.2)',
    borderColor: 'rgba(0, 255, 127, 0.3)',
  },
  '&::before': {
    content: '""',
    position: 'absolute',
    top: 0, left: 0,
    width: '100%', height: '3px',
    background: 'linear-gradient(to right, rgba(0, 255, 127, 0.3), rgba(0, 255, 127, 0.7), rgba(0, 255, 127, 0.3))',
  },
  '&::after': {
    content: '""',
    position: 'absolute',
    top: 0, left: 0,
    width: '100%', height: '100%',
    background: 'linear-gradient(120deg, transparent, rgba(0, 255, 127, 0.05), transparent)',
    transform: 'translateX(-100%)',
  },
  '&:hover::after': {
    animation: `${shimmer} 2s infinite`,
  },
});

const STATUS_COLORS: Record<string, { bg: string; border: string; dot: string; glow: string }> = {
  RUNNING:    { bg: 'rgba(0, 255, 127, 0.15)', border: 'rgba(0, 255, 127, 0.3)', dot: '#00FF7F', glow: 'rgba(0, 255, 127, 0.8)' },
  PENDING:    { bg: 'rgba(255, 193, 7, 0.15)', border: 'rgba(255, 193, 7, 0.3)', dot: '#FFC107', glow: 'rgba(255, 193, 7, 0.8)' },
  STOPPED:    { bg: 'rgba(244, 67, 54, 0.15)', border: 'rgba(244, 67, 54, 0.3)', dot: '#F44336', glow: 'rgba(244, 67, 54, 0.8)' },
  TERMINATED: { bg: 'rgba(128, 128, 128, 0.15)', border: 'rgba(128, 128, 128, 0.3)', dot: '#888888', glow: 'rgba(136, 136, 136, 0.8)' },
};
const DEFAULT_STATUS_COLOR = STATUS_COLORS.TERMINATED;

export const StatusBadge = styled('span')<{ status: string }>(({ status }) => {
  const c = STATUS_COLORS[status] || DEFAULT_STATUS_COLOR;
  return {
    display: 'inline-flex',
    alignItems: 'center',
    color: '#FFFFFF',
    fontWeight: 'medium',
    fontSize: '0.85rem',
    marginBottom: '0.75rem',
    fontFamily: "'Söhne Mono', monospace",
    letterSpacing: '0.5px',
    position: 'relative',
    padding: '4px 12px 4px 24px',
    borderRadius: '12px',
    backgroundColor: c.bg,
    border: `1px solid ${c.border}`,
    '&::before': {
      content: '""',
      position: 'absolute',
      left: '10px', top: '50%',
      transform: 'translateY(-50%)',
      width: '6px', height: '6px',
      borderRadius: '50%',
      backgroundColor: c.dot,
      boxShadow: `0 0 6px ${c.glow}`,
    },
  };
});

export const InstanceId = styled(Typography)({
  fontSize: '0.85rem',
  opacity: 0.7,
  marginBottom: '0.5rem',
  color: '#FFFFFF',
  fontFamily: "'Söhne Mono', monospace",
  letterSpacing: '0.5px',
  padding: '3px 0',
  display: 'inline-block',
  fontWeight: 'normal',
});

export const InstanceDetails = styled(Box)({
  display: 'flex',
  flexWrap: 'wrap',
  gap: '8px',
  marginBottom: '0.75rem',
  alignItems: 'center',
});

export const DetailChip = styled(Chip)({
  backgroundColor: 'rgba(0, 0, 0, 0.3)',
  color: 'rgba(255, 255, 255, 0.8)',
  border: '1px solid rgba(0, 255, 127, 0.2)',
  height: '24px',
  fontSize: '0.75rem',
  fontFamily: "'Söhne Mono', monospace",
  boxShadow: '0 0 4px rgba(0, 255, 127, 0.1)',
  transition: 'all 0.2s ease',
  '& .MuiChip-label': { padding: '0 8px' },
  '&:hover': {
    boxShadow: '0 0 6px rgba(0, 255, 127, 0.2)',
    borderColor: 'rgba(0, 255, 127, 0.3)',
  },
});

export const ActionButtons = styled(Box)({
  display: 'flex',
  gap: '0.5rem',
  marginTop: '1rem',
  flexWrap: 'nowrap',
  justifyContent: 'flex-start',
  backgroundColor: 'rgba(0, 0, 0, 0.2)',
  borderRadius: '6px',
  padding: '8px 10px',
  '& button': {
    transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
    position: 'relative',
    overflow: 'hidden',
    '&::after': {
      content: '""',
      position: 'absolute',
      top: '-50%', left: '-50%',
      width: '200%', height: '200%',
      background: 'radial-gradient(circle, rgba(255,255,255,0.2) 0%, rgba(255,255,255,0) 70%)',
      opacity: 0,
      transform: 'scale(0.5)',
      transition: 'opacity 0.5s, transform 0.5s',
    },
    '&:hover::after': {
      opacity: 1,
      transform: 'scale(1)',
    },
  },
});

export const ActionButton = styled(IconButton, {
  shouldForwardProp: (prop) => prop !== 'component',
})({
  color: 'rgba(255, 255, 255, 0.9)',
  padding: '6px',
  borderRadius: '4px',
  backgroundColor: 'rgba(0, 0, 0, 0.3)',
  transition: 'all 0.2s ease',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  '&:hover': {
    backgroundColor: 'rgba(0, 255, 127, 0.15)',
    transform: 'translateY(-1px)',
    boxShadow: '0 2px 5px rgba(0, 0, 0, 0.2)',
    borderColor: 'rgba(0, 255, 127, 0.3)',
  },
  '&:active': {
    transform: 'translateY(1px)',
    boxShadow: 'none',
  },
  '& svg': { fontSize: '1.2rem' },
  '&.Mui-disabled': {
    opacity: 0.5,
    color: 'rgba(237, 237, 237, 0.5)',
  },
}) as typeof IconButton;

export const NotificationBox = styled(Box)<{ type: 'success' | 'error' | 'info' }>(({ type }) => ({
  position: 'fixed',
  top: '20px', right: '20px',
  padding: '12px 20px',
  borderRadius: '6px',
  color: '#FFFFFF',
  fontFamily: "'Söhne Mono', monospace",
  fontSize: '0.9rem',
  zIndex: 2000,
  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  animation: `${slideIn} 0.3s ease-out`,
  backgroundColor: type === 'success' ? 'rgba(0, 255, 127, 0.2)' :
                  type === 'error' ? 'rgba(244, 67, 54, 0.2)' :
                  'rgba(33, 150, 243, 0.2)',
  border: `1px solid ${type === 'success' ? 'rgba(0, 255, 127, 0.5)' :
                      type === 'error' ? 'rgba(244, 67, 54, 0.5)' :
                      'rgba(33, 150, 243, 0.5)'}`,
}));

export const BackButton = styled(Button)({
  color: '#FFFFFF',
  minWidth: 'auto',
  padding: '8px 12px',
  position: 'relative',
  marginRight: '20px',
  backgroundColor: 'rgba(0, 0, 0, 0.4)',
  border: '1px solid rgba(0, 255, 127, 0.3)',
  borderRadius: '4px',
  fontWeight: 'bold',
  textShadow: '0 0 8px rgba(0, 255, 127, 0.4)',
  transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
  overflow: 'hidden',
  '& svg': { transition: 'transform 0.3s ease' },
  '&:hover': {
    backgroundColor: 'rgba(0, 255, 127, 0.1)',
    borderColor: 'rgba(0, 255, 127, 0.6)',
    transform: 'translateY(-2px)',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2), 0 0 15px rgba(0, 255, 127, 0.2)',
    '& svg': {
      animation: `${slideRight} 0.5s ease infinite alternate`,
    },
  },
  '&:active': {
    transform: 'translateY(1px)',
    '&::after': {
      content: '""',
      position: 'absolute',
      top: '50%', left: '50%',
      width: '5px', height: '5px',
      borderRadius: '50%',
      backgroundColor: 'rgba(0, 255, 127, 0.8)',
      transform: 'translate(-50%, -50%)',
      animation: `${rippleEffect} 0.6s ease-out`,
    },
  },
  '&::before': {
    content: '""',
    position: 'absolute',
    top: 0, left: 0,
    width: '100%', height: '100%',
    background: 'linear-gradient(120deg, transparent, rgba(0, 255, 127, 0.2), transparent)',
    transform: 'translateX(-100%)',
  },
  '&:hover::before': {
    animation: `${shimmer} 1.5s infinite`,
  },
});

export const DIALOG_PAPER_PROPS = {
  sx: {
    backgroundColor: '#121212',
    color: 'white',
    border: '1px solid rgba(0, 255, 127, 0.2)',
    boxShadow: '0 0 10px rgba(0, 255, 127, 0.1)',
  },
};
