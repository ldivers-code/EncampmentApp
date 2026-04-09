import React, { useState, useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { toast } from 'sonner';
import { signHonorAgreement } from '../services/api';
import { Shield, FileText, CheckCircle, ScrollText } from 'lucide-react';

const CADRE_ROLES = ['cadre', 'exec_cadre'];
const STAFF_ROLES = [
  'dcp', 'commander', 'executive_staff', 'training_officer', 'logistics',
  'finance', 'plans_programs', 'staff', 'health_services', 'dining_facility',
  'support_logistics', 'support_comms', 'support_pa', 'support_dining',
  'support_health', 'squadron_commander'
];

const PDF_URLS = {
  cadre: 'https://customer-assets.emergentagent.com/job_90fb572f-92d2-4711-91a4-dde04123d719/artifacts/mifqbc1b_Encampment_Cadre_Honor_AgreementFINAL_f09d4777ca1a8.pdf',
  staff: 'https://customer-assets.emergentagent.com/job_90fb572f-92d2-4711-91a4-dde04123d719/artifacts/1n2h5kih_Senior_Staff_Honor_AgreementFinal_52abf2854fad6.pdf'
};

const CADRE_AGREEMENT = [
  {
    type: 'paragraph',
    text: 'I understand and will uphold the mission, vision, and philosophy of encampment.'
  },
  {
    type: 'section',
    title: 'Mission',
    text: 'The purpose of the cadet encampment is for cadets to develop leadership skills, investigate the aerospace sciences and related careers, commit to a habit of regular exercise, and solidify their moral character.'
  },
  {
    type: 'section',
    title: 'Vision',
    text: 'The vision for the cadet encampment is "an immersion into the full challenges and opportunities of cadet life."'
  },
  {
    type: 'section',
    title: 'Philosophy',
    text: 'Encampment presents the five key traits of cadet life \u2013 the uniform, aerospace themes, opportunities to lead, challenge, and fun (ref: CAPR 60-1, chapter 1) \u2013 in an intensive environment that moves cadets beyond their normal comfort zones for personal growth.'
  },
  {
    type: 'paragraph',
    text: 'I will perform the duties of my position with the CAP Core Values (integrity, respect, excellence, volunteer service) at the forefront of everything I do.'
  },
  {
    type: 'paragraph',
    bold: true,
    text: 'The protection of our students and fellow cadre including their safety, health, and overall well-being will be my number one priority.'
  },
  {
    type: 'bullets',
    items: [
      'I will immediately stop any unsafe situation. Everyone is a safety officer!',
      'I will prioritize the health/well being of the cadets entrusted to my care.',
      'I will give my cadets adequate time to use the bathroom.',
      'I will ensure a cadet with a health concern seeks treatment and I will not interfere with that treatment.',
      'I will work with health services to make sure my cadets have adequate time to take their medication.',
      'I will utilize appropriate intensity and expect my teammates to do the same.',
      'I will report cadet protection issues to the Commander/Activity Director directly while keeping my chain of command in the loop if possible.',
      'I will speak up and share information that could be helpful in problem solving an issue in this area (see something, say something, do something).',
      'I will keep my bunk or room clean and free of safety hazards.',
      'I will communicate with my Training Officer(s) or Senior Directors and rely on them for support and guidance.'
    ]
  },
  {
    type: 'paragraph',
    text: 'I will display a high level of self-discipline, military bearing, and military customs and courtesies in front of all encampment students and when working with cadre and senior staff in a professional setting. I will use my authority as a staff member appropriately.'
  },
  {
    type: 'paragraph',
    text: 'I will take care of myself and set the example to students by eating meals, taking bathroom and rest breaks, getting adequate sleep, addressing health/medical issues, and asking for help when I need it.'
  },
  {
    type: 'paragraph',
    text: 'I will strive to focus on the job at hand which often needs my undivided attention. I will limit usage of cell phones, laptops and other electronic devices for personal matters when I have a break away from the students or when I am off duty.'
  },
  {
    type: 'paragraph',
    text: 'I will follow all CAP and location (base/campus/camp) rules/regulations at all times even when I am "off duty".'
  }
];

const STAFF_AGREEMENT = [
  {
    type: 'paragraph',
    text: 'I understand and will uphold the mission, vision, and philosophy of encampment.'
  },
  {
    type: 'section',
    title: 'Mission',
    text: 'The purpose of the cadet encampment is for cadets to develop leadership skills, investigate the aerospace sciences and related careers, commit to a habit of regular exercise, and solidify their moral character.'
  },
  {
    type: 'section',
    title: 'Vision',
    text: 'The vision for the cadet encampment is "an immersion into the full challenges and opportunities of cadet life."'
  },
  {
    type: 'section',
    title: 'Philosophy',
    text: 'Encampment presents the five key traits of cadet life \u2013 the uniform, aerospace themes, opportunities to lead, challenge, and fun (ref: CAPR 60-1, chapter 1) \u2013 in an intensive environment that moves cadets beyond their normal comfort zones for personal growth.'
  },
  {
    type: 'paragraph',
    text: 'I will perform the duties of my position with the CAP Core Values (integrity, respect, excellence, volunteer service) at the forefront of everything I do.'
  },
  {
    type: 'paragraph',
    bold: true,
    text: 'The protection of our students and cadre including their safety, health, and overall well-being will be my number one priority.'
  },
  {
    type: 'bullets',
    items: [
      'I will immediately stop any unsafe situation. Everyone is a safety officer!',
      'I will prioritize the health/well being of the cadets entrusted to my care.',
      'I will give my cadets adequate time to use the bathroom.',
      'I will not keep a cadet who has a health concern from seeking treatment from health services.',
      'I will work with health services to make sure my cadets have adequate time to take their medication.',
      'I will encourage the cadre I work with to utilize appropriate intensity and intervene in situations where intensity may be moving toward crossing the line.',
      'I will report cadet protection issues to the Commander/Activity Director directly while keeping my chain of command in the loop if possible.',
      'I will speak up and share information that could be helpful in problem solving an issue in this area (see something, say something, do something).',
      'I will keep my desk/office and room clean and free of safety hazards.',
      'I will communicate appropriately and in a way that is constructive with the cadre I work with and my senior staff supervisors.'
    ]
  },
  {
    type: 'paragraph',
    text: 'I will display a high level of self-discipline, military bearing, and military customs and courtesies in front of all encampment students and when working with cadre and senior staff in a professional setting.'
  },
  {
    type: 'paragraph',
    text: 'I will take care of myself and set the example to students and cadre by eating meals, taking bathroom and rest breaks, getting adequate sleep, addressing health/medical issues, and asking for help when I need it.'
  },
  {
    type: 'paragraph',
    text: 'I will strive to focus on the job at hand which often needs my undivided attention. I will limit usage of cell phones, laptops and other electronic devices for personal matters when I have a break away from the students or when I am off duty.'
  }
];

export function getAgreementType(role) {
  if (CADRE_ROLES.includes(role)) return 'cadre';
  if (STAFF_ROLES.includes(role)) return 'staff';
  return null;
}

export function needsHonorAgreement(user) {
  if (!user) return false;
  const type = getAgreementType(user.role);
  if (!type) return false;
  return !user.honor_agreement_signed;
}

const HonorAgreementModal = ({ user, onComplete }) => {
  const [signatureName, setSignatureName] = useState('');
  const [hasScrolled, setHasScrolled] = useState(false);
  const [signing, setSigning] = useState(false);
  const scrollRef = useRef(null);

  const agreementType = getAgreementType(user?.role);
  const agreement = agreementType === 'cadre' ? CADRE_AGREEMENT : STAFF_AGREEMENT;
  const title = agreementType === 'cadre' ? 'Encampment Cadre Honor Agreement' : 'Encampment Senior Staff Honor Agreement';
  const pdfUrl = PDF_URLS[agreementType];

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const handleScroll = () => {
      const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
      if (nearBottom) setHasScrolled(true);
    };
    el.addEventListener('scroll', handleScroll);
    // Check if content fits without scrolling
    if (el.scrollHeight <= el.clientHeight + 60) setHasScrolled(true);
    return () => el.removeEventListener('scroll', handleScroll);
  }, []);

  const handleSign = async () => {
    if (!signatureName.trim()) {
      toast.error('Please type your full name as your signature');
      return;
    }
    setSigning(true);
    try {
      await signHonorAgreement(signatureName.trim());
      toast.success('Honor Agreement signed successfully');
      onComplete();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to sign agreement');
    } finally {
      setSigning(false);
    }
  };

  if (!agreementType) return null;

  return (
    <div className="fixed inset-0 z-[100] bg-black/70 flex items-center justify-center p-4" data-testid="honor-agreement-modal">
      <div className="bg-white w-full max-w-2xl max-h-[95vh] flex flex-col rounded-sm shadow-2xl">
        {/* Header */}
        <div className="bg-[#00205B] text-white p-4 sm:p-5 flex items-center gap-3 flex-shrink-0">
          <Shield className="w-6 h-6 sm:w-8 sm:h-8 flex-shrink-0" />
          <div>
            <h2 className="font-black uppercase text-sm sm:text-base tracking-tight" style={{ fontFamily: 'Chivo, sans-serif' }}>
              {title}
            </h2>
            <p className="text-blue-200 text-xs mt-0.5">
              Tennessee Wing Civil Air Patrol - 2026 Encampment
            </p>
          </div>
        </div>

        {/* Agreement Body */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 text-sm text-slate-700 leading-relaxed"
          data-testid="agreement-body"
        >
          {agreement.map((block, i) => {
            if (block.type === 'section') {
              return (
                <div key={i}>
                  <p className="font-bold text-[#00205B] text-xs uppercase tracking-wider mb-1">{block.title}</p>
                  <p className="italic text-slate-600">{block.text}</p>
                </div>
              );
            }
            if (block.type === 'bullets') {
              return (
                <ul key={i} className="space-y-2 pl-1">
                  {block.items.map((item, j) => (
                    <li key={j} className="flex items-start gap-2">
                      <span className="mt-1.5 w-1.5 h-1.5 bg-[#00205B] rounded-full flex-shrink-0" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              );
            }
            return (
              <p key={i} className={block.bold ? 'font-bold text-[#00205B]' : ''}>
                {block.text}
              </p>
            );
          })}

          {/* PDF Download Link */}
          {pdfUrl && (
            <div className="pt-2 border-t border-slate-200">
              <a
                href={pdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-xs text-[#00205B] hover:underline font-medium"
                data-testid="download-agreement-pdf"
              >
                <FileText className="w-3.5 h-3.5" />
                Download Original PDF
              </a>
            </div>
          )}
        </div>

        {/* Scroll indicator */}
        {!hasScrolled && (
          <div className="text-center py-2 bg-amber-50 border-t border-amber-200 flex-shrink-0">
            <div className="flex items-center justify-center gap-2 text-xs text-amber-700 font-medium">
              <ScrollText className="w-3.5 h-3.5" />
              Please scroll down to read the full agreement
            </div>
          </div>
        )}

        {/* Signature Section */}
        <div className="border-t border-slate-200 p-4 sm:p-5 flex-shrink-0 bg-slate-50 space-y-3">
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-600 font-bold block mb-1.5">
              Digital Signature (Type Your Full Name)
            </label>
            <Input
              value={signatureName}
              onChange={(e) => setSignatureName(e.target.value)}
              placeholder="e.g. John A. Smith"
              className="rounded-sm text-base font-medium"
              style={{ fontFamily: 'cursive, serif' }}
              data-testid="honor-signature-input"
              disabled={!hasScrolled}
            />
          </div>
          <div className="flex items-center justify-between gap-3">
            <p className="text-[10px] text-slate-400">
              Date: {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
            </p>
            <Button
              onClick={handleSign}
              disabled={!hasScrolled || !signatureName.trim() || signing}
              className="bg-[#00205B] hover:bg-[#001540] rounded-sm px-6"
              data-testid="honor-sign-btn"
            >
              <CheckCircle className="w-4 h-4 mr-2" />
              {signing ? 'Signing...' : 'I Agree & Sign'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HonorAgreementModal;
