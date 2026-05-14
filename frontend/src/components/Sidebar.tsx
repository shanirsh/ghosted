import React, { useState } from 'react';
import { styled, keyframes } from '@mui/material/styles';
import { Drawer, List, ListItem, ListItemIcon, ListItemText, IconButton } from '@mui/material';
import CloudIcon from '@mui/icons-material/Cloud';
import HomeIcon from '@mui/icons-material/Home';
import MenuIcon from '@mui/icons-material/Menu';
import CloseIcon from '@mui/icons-material/Close';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';

const glow = keyframes`
  0% { box-shadow: 0 0 5px rgba(0, 255, 127, 0.2); }
  50% { box-shadow: 0 0 15px rgba(0, 255, 127, 0.4); }
  100% { box-shadow: 0 0 5px rgba(0, 255, 127, 0.2); }
`;

const SidebarContainer = styled(Drawer)({
  width: 220, flexShrink: 0,
  '& .MuiDrawer-paper': {
    width: 220, backgroundColor: '#0A0A0A', color: '#FFFFFF',
    borderRight: '1px solid rgba(0, 255, 127, 0.2)',
    boxShadow: '0 0 20px rgba(0, 0, 0, 0.7)',
    animation: `${glow} 4s ease-in-out infinite`,
    transition: 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
  },
});

const SidebarHeader = styled('div')({
  display: 'flex', alignItems: 'center', padding: '16px 20px',
  borderBottom: '1px solid rgba(0, 255, 127, 0.2)',
  boxShadow: '0 4px 10px -4px rgba(0, 0, 0, 0.3)',
  position: 'relative', backgroundColor: 'rgba(0, 0, 0, 0.3)',
  '&:after': {
    content: '""', position: 'absolute', bottom: 0, left: '10%', width: '80%', height: '1px',
    background: 'linear-gradient(to right, transparent, rgba(0, 255, 127, 0.4), transparent)',
  },
});

const SidebarTitle = styled('h2')({
  margin: 0, fontSize: '1.5rem', color: '#FFFFFF', fontWeight: '800',
  letterSpacing: '4px', textShadow: '0 0 10px rgba(0, 255, 127, 0.7)',
  textTransform: 'uppercase', fontFamily: "'Söhne Mono', monospace",
  transition: 'all 0.3s ease',
  '&:hover': { textShadow: '0 0 15px rgba(0, 255, 127, 0.9)', letterSpacing: '5px' },
});

const NavItem = styled(ListItem)<{ active?: boolean }>(({ active }) => ({
  padding: '14px 0 14px 1.5rem', cursor: 'pointer', transition: 'all 0.3s ease',
  marginBottom: '10px', borderRadius: '0 4px 4px 0',
  display: 'flex', alignItems: 'center', gap: '0.4rem',
  ...(active && {
    backgroundColor: 'rgba(0, 255, 127, 0.1)',
    borderLeft: '3px solid #00FF7F',
    boxShadow: 'inset 0 0 10px rgba(0, 255, 127, 0.2)',
    '& .MuiListItemText-primary': { fontWeight: 'bold', color: '#00FF7F', textShadow: '0 0 10px rgba(0, 255, 127, 0.6)' },
  }),
  ...(!active && {
    '&:hover': {
      backgroundColor: 'rgba(0, 255, 127, 0.1)',
      borderLeft: '3px solid #00FF7F',
      transform: 'translateX(5px)',
      boxShadow: 'inset 0 0 10px rgba(0, 255, 127, 0.2)',
    },
  }),
}));

const NavItemText = styled(ListItemText)({
  '& .MuiListItemText-primary': {
    color: '#FFFFFF', fontSize: '0.95rem', fontWeight: 'bold',
    letterSpacing: '1.5px', fontFamily: "'Söhne Mono', monospace",
    textShadow: '0 0 8px rgba(0, 255, 127, 0.5)', textTransform: 'uppercase',
    transition: 'all 0.2s ease',
  },
  marginLeft: '4px',
});

const MenuButton = styled(IconButton)({
  position: 'fixed', top: '16px', left: '16px', zIndex: 1200,
  color: 'rgba(0, 255, 127, 0.85)', backgroundColor: 'rgba(0, 0, 0, 0.6)',
  boxShadow: '0 0 10px rgba(0, 255, 127, 0.3)',
  '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.75)', boxShadow: '0 0 15px rgba(0, 255, 127, 0.6)', color: '#00FF7F' },
  transition: 'all 0.2s ease',
});

interface SidebarProps {
  roleArn: string;
  region: string;
  externalId: string;
  onNavigate: (page: string) => void;
  currentPage?: string;
}

const NAV_ITEMS = [
  { page: 'chat', label: 'Home', icon: HomeIcon },
  { page: 'deployments', label: 'MY DEPLOYMENTS', icon: CloudIcon },
];

const Sidebar: React.FC<SidebarProps> = ({ onNavigate, currentPage = 'chat' }) => {
  const [open, setOpen] = useState(false);

  const handleNavigation = (page: string) => { onNavigate(page); setOpen(false); };

  return (
    <>
      <MenuButton onClick={() => setOpen(!open)} aria-label="menu">
        {open ? <CloseIcon /> : <MenuIcon />}
      </MenuButton>

      <SidebarContainer variant="persistent" anchor="left" open={open} ModalProps={{ keepMounted: true }}>
        <SidebarHeader>
          <SidebarTitle>Ghosted Dashboard</SidebarTitle>
          <IconButton onClick={() => setOpen(false)} aria-label="minimize" sx={{ color: 'rgba(0, 255, 127, 0.8)', '&:hover': { backgroundColor: 'rgba(0, 255, 127, 0.15)', color: '#00FF7F' } }}>
            <ChevronLeftIcon />
          </IconButton>
        </SidebarHeader>

        <List sx={{ padding: '20px 0' }}>
          {NAV_ITEMS.map(({ page, label, icon: Icon }) => (
            <NavItem key={page} active={currentPage === page} onClick={() => handleNavigation(page)}>
              <ListItemIcon sx={{ minWidth: 'auto' }}>
                <Icon style={{ color: '#00FF7F', fontSize: '1.4rem' }} />
              </ListItemIcon>
              <NavItemText primary={label} />
            </NavItem>
          ))}
        </List>
      </SidebarContainer>
    </>
  );
};

export default Sidebar;
