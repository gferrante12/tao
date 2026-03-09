# echo "cleanup ChargeTemplatePos v0 in /dybfs/users/xuhangkun/SimTAO/offline/tao_offline/Simulation/DetSim"

if test "${CMTROOT}" = ""; then
  CMTROOT=/cvmfs/juno.ihep.ac.cn/centos7_amd64_gcc830/Pre-Release/J20v2r0-branch/ExternalLibs/CMT/v1r26; export CMTROOT
fi
. ${CMTROOT}/mgr/setup.sh
cmtChargeTemplatePostempfile=`${CMTROOT}/mgr/cmt -quiet build temporary_name`
if test ! $? = 0 ; then cmtChargeTemplatePostempfile=/tmp/cmt.$$; fi
${CMTROOT}/mgr/cmt cleanup -sh -pack=ChargeTemplatePos -version=v0 -path=/dybfs/users/xuhangkun/SimTAO/offline/tao_offline/Simulation/DetSim  $* >${cmtChargeTemplatePostempfile}
if test $? != 0 ; then
  echo >&2 "${CMTROOT}/mgr/cmt cleanup -sh -pack=ChargeTemplatePos -version=v0 -path=/dybfs/users/xuhangkun/SimTAO/offline/tao_offline/Simulation/DetSim  $* >${cmtChargeTemplatePostempfile}"
  cmtcleanupstatus=2
  /bin/rm -f ${cmtChargeTemplatePostempfile}
  unset cmtChargeTemplatePostempfile
  return $cmtcleanupstatus
fi
cmtcleanupstatus=0
. ${cmtChargeTemplatePostempfile}
if test $? != 0 ; then
  cmtcleanupstatus=2
fi
/bin/rm -f ${cmtChargeTemplatePostempfile}
unset cmtChargeTemplatePostempfile
return $cmtcleanupstatus

