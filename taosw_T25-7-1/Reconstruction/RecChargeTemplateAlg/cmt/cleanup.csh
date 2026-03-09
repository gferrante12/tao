# echo "cleanup ChargeTemplatePos v0 in /dybfs/users/xuhangkun/SimTAO/offline/tao_offline/Simulation/DetSim"

if ( $?CMTROOT == 0 ) then
  setenv CMTROOT /cvmfs/juno.ihep.ac.cn/centos7_amd64_gcc830/Pre-Release/J20v2r0-branch/ExternalLibs/CMT/v1r26
endif
source ${CMTROOT}/mgr/setup.csh
set cmtChargeTemplatePostempfile=`${CMTROOT}/mgr/cmt -quiet build temporary_name`
if $status != 0 then
  set cmtChargeTemplatePostempfile=/tmp/cmt.$$
endif
${CMTROOT}/mgr/cmt cleanup -csh -pack=ChargeTemplatePos -version=v0 -path=/dybfs/users/xuhangkun/SimTAO/offline/tao_offline/Simulation/DetSim  $* >${cmtChargeTemplatePostempfile}
if ( $status != 0 ) then
  echo "${CMTROOT}/mgr/cmt cleanup -csh -pack=ChargeTemplatePos -version=v0 -path=/dybfs/users/xuhangkun/SimTAO/offline/tao_offline/Simulation/DetSim  $* >${cmtChargeTemplatePostempfile}"
  set cmtcleanupstatus=2
  /bin/rm -f ${cmtChargeTemplatePostempfile}
  unset cmtChargeTemplatePostempfile
  exit $cmtcleanupstatus
endif
set cmtcleanupstatus=0
source ${cmtChargeTemplatePostempfile}
if ( $status != 0 ) then
  set cmtcleanupstatus=2
endif
/bin/rm -f ${cmtChargeTemplatePostempfile}
unset cmtChargeTemplatePostempfile
exit $cmtcleanupstatus

