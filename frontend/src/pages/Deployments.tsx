import React, { useState, useEffect, useRef } from 'react';
import {
  Typography, Box, IconButton, Button, Tooltip, Grid, Divider,
  MenuItem, Select, FormControl,
  Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, TextField,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import DeleteIcon from '@mui/icons-material/Delete';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import TerminalIcon from '@mui/icons-material/Terminal';
import EditIcon from '@mui/icons-material/Edit';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import RefreshIcon from '@mui/icons-material/Refresh';

import {
  PageContainer, PageHeader, PageTitle, DeploymentCard, StatusBadge,
  InstanceId, InstanceDetails, DetailChip, ActionButtons, ActionButton,
  NotificationBox, BackButton, DIALOG_PAPER_PROPS,
} from './Deployments.styles';

interface DeploymentProps {
  id: string;
  name?: string;
  status: 'RUNNING' | 'PENDING' | 'STOPPED' | 'TERMINATED' | string;
  type?: string;
  region?: string;
  publicIp?: string;
  privateIp?: string;
  consoleLink: string;
}

interface DeploymentsPageProps {
  roleArn: string;
  region: string;
  externalId: string;
  onBack: () => void;
}

type SortOption = 'status' | 'name' | 'newest';

const STATUS_ORDER: Record<string, number> = { RUNNING: 0, PENDING: 1, STOPPED: 2, TERMINATED: 3 };

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const DeploymentsPage: React.FC<DeploymentsPageProps> = ({ roleArn, region, externalId, onBack }) => {
  const [deployments, setDeployments] = useState<DeploymentProps[]>([]);
  const [loading, setLoading] = useState(false);
  const [sortBy, setSortBy] = useState<SortOption>('status');
  const [actionInProgress, setActionInProgress] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState<{ open: boolean; instanceId: string; instanceName: string } | null>(null);
  const [renameDialog, setRenameDialog] = useState<{ open: boolean; instanceId: string; currentName: string } | null>(null);
  const [notification, setNotification] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);

  const sortedDeployments = [...deployments].sort((a, b) => {
    if (sortBy === 'status') return (STATUS_ORDER[a.status] ?? 999) - (STATUS_ORDER[b.status] ?? 999);
    if (sortBy === 'name') return (a.name || '').localeCompare(b.name || '');
    return b.id.localeCompare(a.id);
  });

  const showNotification = (message: string, type: 'success' | 'error' | 'info') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const apiCall = async (command: string, extraBody: Record<string, unknown> = {}) => {
    const response = await fetch(`${API_URL}/api/ai/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        command,
        role_arn: roleArn,
        region,
        external_id: externalId,
        ...extraBody,
      }),
    });
    if (!response.ok) throw new Error(response.statusText);
    const data = await response.json();
    if (data?.success === false) throw new Error(data.message || 'Operation failed');
    return data;
  };

  const fetchDeployments = async () => {
    if (!roleArn || !region || !externalId) return;
    try {
      setLoading(true);
      const data = await apiCall('list my ec2 instances');

      const instances: any[] =
        (Array.isArray(data?.data) ? data.data : null) ||
        data?.data?.instances ||
        data?.instances ||
        data?.data?.items ||
        [];

      const responseRegion = data?.region || data?.data?.region || region;

      if (instances.length === 0) {
        setDeployments([]);
        showNotification('No EC2 instances found in your account', 'info');
        return;
      }

      setDeployments(instances.map((inst: any) => {
        const id = inst.id || inst.instance_id || inst.InstanceId || 'Unknown';
        const rawState = inst.state || inst.State?.Name || inst.status || 'unknown';
        const instanceRegion = inst.region || responseRegion;

        return {
          id,
          name: inst.name || inst.Name || inst.Tags?.find((t: any) => t.Key === 'Name')?.Value || 'Unnamed Instance',
          status: rawState === 'running' ? 'RUNNING' :
                  rawState === 'pending' ? 'PENDING' :
                  rawState === 'stopped' ? 'STOPPED' :
                  rawState.toUpperCase(),
          type: inst.type || inst.instance_type || inst.InstanceType || 't2.micro',
          region: instanceRegion,
          publicIp: inst.public_ip === 'N/A' ? undefined : inst.public_ip || inst.PublicIpAddress,
          privateIp: inst.private_ip || inst.PrivateIpAddress || 'N/A',
          consoleLink: inst.console_link ||
            `https://${instanceRegion}.console.aws.amazon.com/ec2/home?region=${instanceRegion}#InstanceDetails:instanceId=${id}`,
        };
      }));
    } catch (error) {
      showNotification(`Failed to fetch deployments: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
      setDeployments([]);
    } finally {
      setLoading(false);
    }
  };

  const handleInstanceAction = async (instanceId: string, action: 'start' | 'stop' | 'terminate') => {
    try {
      setActionInProgress(true);
      showNotification(`${action.charAt(0).toUpperCase() + action.slice(1)}ing instance ${instanceId.slice(0, 8)}...`, 'info');
      await apiCall(`${action} ec2 instance ${instanceId}`, { from_ui: true });
      showNotification(
        `Successfully ${action === 'terminate' ? 'terminated' : action + 'ed'} instance ${instanceId.slice(0, 8)}...`,
        'success',
      );
      setTimeout(() => { fetchDeployments(); setActionInProgress(false); }, 5000);
    } catch (error) {
      setActionInProgress(false);
      showNotification(`Failed to ${action} instance: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
    }
  };

  const handleRenameInstance = async (instanceId: string, newName: string) => {
    try {
      setActionInProgress(true);
      if (!roleArn || !region || !externalId) return;
      await apiCall(`rename ec2 instance ${instanceId} to ${newName}`);
      setDeployments(prev => prev.map(d => d.id === instanceId ? { ...d, name: newName } : d));
      showNotification(`Instance renamed to ${newName}`, 'success');
    } catch (error) {
      showNotification(`Failed to rename instance: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
    } finally {
      setActionInProgress(false);
    }
  };

  useEffect(() => {
    fetchDeployments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <PageContainer maxWidth="lg">
      {notification && <NotificationBox type={notification.type}>{notification.message}</NotificationBox>}

      <PageHeader>
        <BackButton onClick={onBack}><ArrowBackIcon /></BackButton>
        <PageTitle variant="h1">MY DEPLOYMENTS</PageTitle>
      </PageHeader>

      {!loading && deployments.length > 0 && (
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: '1.2rem', alignItems: 'center' }}>
          <Typography variant="body2" sx={{ color: '#00FF7F', mr: '8px', whiteSpace: 'nowrap', fontWeight: 'bold' }}>
            SORT BY
          </Typography>
          <FormControl size="small" sx={{ width: '120px', minWidth: '120px' }}>
            <Select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              sx={{
                color: 'rgba(255, 255, 255, 0.95)',
                '.MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(0, 255, 127, 0.3)' },
                '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(0, 255, 127, 0.5)' },
                '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(0, 255, 127, 0.5)' },
                '.MuiSvgIcon-root': { color: 'rgba(255, 255, 255, 0.7)' },
              }}
            >
              <MenuItem value="status">Status</MenuItem>
              <MenuItem value="name">Name</MenuItem>
              <MenuItem value="newest">Newest</MenuItem>
            </Select>
          </FormControl>
        </Box>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px' }}>
          <Typography sx={{ opacity: 0.7 }}>Loading your deployments...</Typography>
        </Box>
      ) : deployments.length === 0 ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center',
                   height: '300px', backgroundColor: 'rgba(0, 0, 0, 0.2)', borderRadius: '8px', padding: '2rem' }}>
          <Typography variant="h6" sx={{ opacity: 0.7, mb: '1rem' }}>
            You haven't deployed anything yet
          </Typography>
          <Typography sx={{ opacity: 0.5, textAlign: 'center', maxWidth: '400px' }}>
            When you create EC2 instances, they will appear here for easy management.
          </Typography>
        </Box>
      ) : (
        <Box sx={{ maxHeight: 'calc(100vh - 220px)', overflowY: 'auto', pr: '8px' }}>
          <Grid container spacing={2}>
            {sortedDeployments.map((deployment) => (
              <Grid item xs={12} md={6} key={deployment.id}>
                <DeploymentCard elevation={0}>
                  <Box sx={{ display: 'flex', justifyContent: 'flex-start', alignItems: 'flex-start', mb: '0.5rem' }}>
                    <StatusBadge status={deployment.status}>
                      {deployment.status.charAt(0) + deployment.status.slice(1).toLowerCase()}
                    </StatusBadge>
                  </Box>

                  <Box sx={{ display: 'flex', alignItems: 'center', mb: '0.5rem' }}>
                    <Typography variant="h6" fontWeight="bold" sx={{ mr: '4px' }}>
                      {deployment.name}
                    </Typography>
                    <Tooltip title="Rename instance">
                      <IconButton
                        size="small"
                        onClick={() => setRenameDialog({ open: true, instanceId: deployment.id, currentName: deployment.name || '' })}
                        disabled={actionInProgress}
                        sx={{
                          p: 0, height: '20px', width: '20px', opacity: 0.7,
                          '&:hover': { opacity: 1, backgroundColor: 'rgba(0, 255, 127, 0.1)' },
                        }}
                      >
                        <EditIcon sx={{ fontSize: '14px', color: 'rgba(255, 255, 255, 0.7)' }} />
                      </IconButton>
                    </Tooltip>
                  </Box>

                  <InstanceId>{deployment.id}</InstanceId>

                  <InstanceDetails>
                    {deployment.type && <DetailChip label={deployment.type} />}
                    <DetailChip
                      icon={<LocationOnIcon sx={{ fontSize: '0.9rem' }} />}
                      label={region || 'us-east-1'}
                      sx={{ backgroundColor: 'rgba(0, 0, 0, 0.4)', borderColor: 'rgba(0, 255, 127, 0.25)', boxShadow: '0 0 5px rgba(0, 255, 127, 0.15)' }}
                    />
                    {deployment.privateIp && <DetailChip label={deployment.privateIp} />}
                    {deployment.publicIp && <DetailChip label={`Public: ${deployment.publicIp}`} />}
                  </InstanceDetails>

                  <Divider sx={{ my: 2, backgroundColor: 'rgba(255, 255, 255, 0.1)' }} />

                  <ActionButtons>
                    <Box sx={{ display: 'flex', gap: '2px', alignItems: 'center' }}>
                      <Tooltip title="Start Instance">
                        <span>
                          <ActionButton
                            onClick={() => handleInstanceAction(deployment.id, 'start')}
                            disabled={deployment.status === 'RUNNING' || actionInProgress}
                            size="small"
                            aria-label="Start instance"
                          >
                            <PlayArrowIcon />
                          </ActionButton>
                        </span>
                      </Tooltip>
                      <Tooltip title="Stop Instance">
                        <span>
                          <ActionButton
                            onClick={() => handleInstanceAction(deployment.id, 'stop')}
                            disabled={deployment.status === 'STOPPED' || actionInProgress}
                            size="small"
                            aria-label="Stop instance"
                          >
                            <StopIcon />
                          </ActionButton>
                        </span>
                      </Tooltip>
                    </Box>
                    <Box sx={{ display: 'flex', gap: '2px', ml: 'auto' }}>
                      <Tooltip title="Open Console">
                        <span>
                          <Button
                            href={deployment.consoleLink}
                            target="_blank"
                            rel="noopener noreferrer"
                            size="small"
                            aria-label="Open console"
                            sx={{
                              minWidth: 'unset', p: '6px',
                              color: 'rgba(255, 255, 255, 0.9)', backgroundColor: 'rgba(0, 0, 0, 0.3)',
                              border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '4px',
                              '&:hover': { backgroundColor: 'rgba(0, 255, 127, 0.15)', borderColor: 'rgba(0, 255, 127, 0.3)' },
                            }}
                          >
                            <TerminalIcon fontSize="small" />
                          </Button>
                        </span>
                      </Tooltip>
                      <Tooltip title="Terminate Instance">
                        <ActionButton
                          onClick={() => setConfirmDialog({ open: true, instanceId: deployment.id, instanceName: deployment.name || 'Unnamed Instance' })}
                          disabled={actionInProgress}
                          size="small"
                          aria-label="Terminate instance"
                          sx={{ color: 'rgba(244, 67, 54, 0.8)' }}
                        >
                          <DeleteIcon />
                        </ActionButton>
                      </Tooltip>
                    </Box>
                  </ActionButtons>
                </DeploymentCard>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}

      <Box mt={4} display="flex" justifyContent="center">
        <Button
          variant="outlined"
          onClick={fetchDeployments}
          startIcon={<RefreshIcon />}
          disabled={loading}
          sx={{
            borderColor: 'rgba(0, 255, 127, 0.5)', color: '#00FF7F',
            '&:hover': { borderColor: '#00FF7F', backgroundColor: 'rgba(0, 255, 127, 0.08)' },
          }}
        >
          {loading ? 'Refreshing...' : 'Refresh Deployments'}
        </Button>
      </Box>

      {/* Terminate confirmation */}
      <Dialog open={confirmDialog?.open || false} onClose={() => setConfirmDialog(null)} PaperProps={DIALOG_PAPER_PROPS}>
        <DialogTitle sx={{ color: 'rgba(244, 67, 54, 0.9)' }}>Terminate Instance</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ color: 'rgba(255, 255, 255, 0.8)' }}>
            Are you sure you want to terminate instance <strong>{confirmDialog?.instanceName || 'Unknown'}</strong> ({confirmDialog?.instanceId || ''})? This action cannot be undone, and all data on the instance will be lost.
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ padding: '16px' }}>
          <Button onClick={() => setConfirmDialog(null)} sx={{ color: 'rgba(255, 255, 255, 0.7)' }}>
            Cancel
          </Button>
          <Button
            onClick={() => {
              if (confirmDialog) {
                handleInstanceAction(confirmDialog.instanceId, 'terminate');
                setConfirmDialog(null);
              }
            }}
            sx={{
              backgroundColor: 'rgba(244, 67, 54, 0.1)', color: 'rgba(244, 67, 54, 0.9)',
              '&:hover': { backgroundColor: 'rgba(244, 67, 54, 0.2)' },
            }}
            autoFocus
          >
            Terminate
          </Button>
        </DialogActions>
      </Dialog>

      {/* Rename dialog */}
      <Dialog open={renameDialog?.open || false} onClose={() => setRenameDialog(null)} PaperProps={DIALOG_PAPER_PROPS}>
        <DialogTitle sx={{ color: 'rgba(0, 255, 127, 0.9)' }}>Rename Instance</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ color: 'rgba(255, 255, 255, 0.8)', mb: '16px' }}>
            Enter a new name for instance {renameDialog?.instanceId || ''}:
          </DialogContentText>
          <TextField
            autoFocus
            margin="dense"
            label="Instance Name"
            type="text"
            fullWidth
            defaultValue={renameDialog?.currentName || ''}
            inputRef={renameInputRef}
            variant="outlined"
            InputLabelProps={{ sx: { color: 'rgba(255, 255, 255, 0.7)' } }}
            InputProps={{
              sx: {
                color: 'white',
                '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(0, 255, 127, 0.3)' },
                '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(0, 255, 127, 0.5)' },
                '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(0, 255, 127, 0.7)' },
              },
            }}
          />
        </DialogContent>
        <DialogActions sx={{ padding: '16px' }}>
          <Button onClick={() => setRenameDialog(null)} sx={{ color: 'rgba(255, 255, 255, 0.7)' }}>
            Cancel
          </Button>
          <Button
            onClick={() => {
              if (renameDialog) {
                const newName = renameInputRef.current?.value?.trim() || '';
                if (newName) {
                  handleRenameInstance(renameDialog.instanceId, newName);
                  setRenameDialog(null);
                }
              }
            }}
            sx={{
              backgroundColor: 'rgba(0, 255, 127, 0.1)', color: 'rgba(0, 255, 127, 0.9)',
              '&:hover': { backgroundColor: 'rgba(0, 255, 127, 0.2)' },
            }}
            disabled={actionInProgress}
            autoFocus
          >
            Rename
          </Button>
        </DialogActions>
      </Dialog>
    </PageContainer>
  );
};

export default DeploymentsPage;
