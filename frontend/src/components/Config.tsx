import React, { useState, useRef, useEffect } from 'react';
import { Typography, IconButton } from '@mui/material';
import { ArrowRight, Copy, ExternalLink } from 'react-feather';
import logo from '../images/update-removebg-preview.png';

import {
  ConfigContainer, HeroSection, HeroContent, LogoImage, WordmarkContainer,
  HeroTitle, HeroSubtitle, ConfigSection, Separator, ArnInput,
  ConnectButton, DeployRoleButton, DeployButton, GhostedMessage,
  Particle, ParticleContainer, PageTransition, GhostLogo, ConnectingText,
} from './Config.styles';

interface ConfigProps {
  onConfigSubmit: (config: { roleArn: string; awsRegion: string; externalId: string }) => Promise<void>;
  ghostOpsAccountId: string;
}

const Config: React.FC<ConfigProps> = ({ onConfigSubmit, ghostOpsAccountId }) => {
  const [roleArn, setRoleArn] = useState('');
  const [externalId, setExternalId] = useState('');
  const [awsRegion, setAwsRegion] = useState('us-east-1');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [showWizard, setShowWizard] = useState(false);
  const [showTransition, setShowTransition] = useState(false);

  const configRef = useRef<HTMLDivElement>(null);
  const logoRef = useRef<HTMLImageElement>(null);
  const wordmarkRef = useRef<HTMLDivElement>(null);

  const [isHitting, setIsHitting] = useState(false);
  const [isFloating, setIsFloating] = useState(false);
  const [isVanishing, setIsVanishing] = useState(false);
  const [isAppearing, setIsAppearing] = useState(false);
  const [showGhostedMessage, setShowGhostedMessage] = useState(false);

  useEffect(() => {
    const startAnimationSequence = () => {
      setIsFloating(true);
      setTimeout(() => { setIsFloating(false); setIsHitting(true); }, 4000);
      setTimeout(() => { setIsVanishing(true); setIsHitting(false); setIsFloating(true); }, 4400);
      setTimeout(() => setShowGhostedMessage(true), 4800);
      setTimeout(() => setShowGhostedMessage(false), 5800);
      setTimeout(() => { setIsVanishing(false); setIsAppearing(true); }, 6200);
      setTimeout(() => { setIsAppearing(false); startAnimationSequence(); }, 7000);
    };
    startAnimationSequence();
  }, []);

  useEffect(() => {
    localStorage.removeItem('externalId');
    setExternalId('');
  }, []);

  const handleDeployRole = () => {
    setShowWizard(true);
    setTimeout(() => configRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 100);
  };

  const validateRoleArn = (arn: string) => /^arn:aws:iam::\d{12}:role\/[a-zA-Z0-9_+=,.@/-]+$/.test(arn);

  const handleSubmit = async () => {
    if (!validateRoleArn(roleArn)) {
      alert('Please enter a valid Role ARN');
      return;
    }
    setIsSubmitting(true);
    try {
      setShowTransition(true);
      await onConfigSubmit({ roleArn, awsRegion, externalId });
      setIsSuccess(true);
    } catch {
      setShowTransition(false);
      setIsSubmitting(false);
    }
  };

  const handleOpenCloudFormation = () => {
    if (!ghostOpsAccountId) {
      alert('Set REACT_APP_GHOSTED_ACCOUNT_ID before launching the CloudFormation template.');
      return;
    }
    const roleExternalId = externalId || crypto.randomUUID();
    setExternalId(roleExternalId);

    const params = new URLSearchParams({
      templateURL: 'https://ghosted-public.s3.us-east-1.amazonaws.com/iam/ghosted-role.yaml',
      param_ExternalId: roleExternalId,
      param_GhostedAccountId: ghostOpsAccountId,
    });
    window.open(`https://console.aws.amazon.com/cloudformation/home?region=${awsRegion}#/stacks/create/review?${params}`, '_blank');
  };

  return (
    <ConfigContainer>
      <ParticleContainer>
        {Array.from({ length: 20 }).map((_, i) => (
          <Particle key={i} style={{ '--particle-index': i, left: `${Math.random() * 100}%`, top: `${Math.random() * 100}%` } as React.CSSProperties} />
        ))}
      </ParticleContainer>

      <HeroSection>
        <HeroContent>
          <LogoImage ref={logoRef} src={logo} alt="ghosted logo" className={`${isHitting ? 'hitting' : ''} ${isFloating ? 'floating' : ''}`} />
          <WordmarkContainer ref={wordmarkRef} className={`${isVanishing ? 'vanishing' : ''} ${isAppearing ? 'appearing' : ''}`}>
            {Array.from('ghosted').map((char, i) => (
              <span key={i} style={{ '--char-index': i } as React.CSSProperties}>{char}</span>
            ))}
          </WordmarkContainer>
          <GhostedMessage className={showGhostedMessage ? 'visible' : ''}>you've been ghosted.</GhostedMessage>
          <HeroTitle>because the cloud should be this easy</HeroTitle>
          <HeroSubtitle>no aws console. no cli. just ghosted.</HeroSubtitle>
          <DeployButton variant="contained" onClick={handleDeployRole} disabled={isSubmitting}>
            {isSubmitting ? 'deploying...' : 'ghosted'}
            <ArrowRight className="button-icon" />
          </DeployButton>
        </HeroContent>
      </HeroSection>

      {showWizard && (
        <ConfigSection ref={configRef}>
          <Typography variant="h4" gutterBottom sx={{ fontSize: '32px', fontWeight: 500, mb: '16px' }}>
            ready to connect ghosted to your aws?
          </Typography>
          <Typography variant="body1" sx={{ color: 'rgba(255, 255, 255, 0.7)', mb: '40px' }}>
            it only takes a minute — no setup files, no stress.
          </Typography>

          <DeployRoleButton variant="contained" onClick={handleOpenCloudFormation} startIcon={<ExternalLink />}>
            deploy role to aws
          </DeployRoleButton>

          <Separator>paste role arn</Separator>
          <ArnInput>
            <input type="text" value={roleArn} onChange={(e) => setRoleArn(e.target.value)} placeholder="paste role arn" />
            <IconButton onClick={() => navigator.clipboard.writeText(roleArn)}>
              <img src={logo} alt="copy" style={{ width: '24px', height: '24px' }} />
            </IconButton>
          </ArnInput>

          <Separator>external id</Separator>
          <ArnInput>
            <input type="text" value={externalId} onChange={(e) => setExternalId(e.target.value)} placeholder="paste external id" />
            <IconButton onClick={() => navigator.clipboard.writeText(externalId)}>
              <Copy size={18} />
            </IconButton>
          </ArnInput>

          <Separator>aws region</Separator>
          <ArnInput>
            <select value={awsRegion} onChange={(e) => setAwsRegion(e.target.value)}>
              <option value="us-east-1">US East (N. Virginia)</option>
              <option value="us-east-2">US East (Ohio)</option>
              <option value="us-west-1">US West (N. California)</option>
              <option value="us-west-2">US West (Oregon)</option>
              <option value="eu-west-1">EU (Ireland)</option>
              <option value="eu-central-1">EU (Frankfurt)</option>
              <option value="ap-northeast-1">Asia Pacific (Tokyo)</option>
              <option value="ap-southeast-1">Asia Pacific (Singapore)</option>
              <option value="ap-southeast-2">Asia Pacific (Sydney)</option>
            </select>
          </ArnInput>

          <ConnectButton variant="contained" onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? 'connecting...' : 'connect & continue'}
          </ConnectButton>

          {isSuccess && (
            <div style={{ textAlign: 'center', marginTop: '40px' }}>
              <Typography variant="h5" gutterBottom sx={{ fontSize: '24px', fontWeight: 500, mt: '24px' }}>
                you're all set. ghosted has entered the chat.
              </Typography>
              <Typography variant="body1" sx={{ color: '#4CAF50' }}>connected successfully</Typography>
            </div>
          )}
        </ConfigSection>
      )}

      <PageTransition className={showTransition ? 'active' : ''}>
        <GhostLogo bgUrl={logo} />
        <ConnectingText>connecting to ghosted</ConnectingText>
      </PageTransition>
    </ConfigContainer>
  );
};

export default Config;
