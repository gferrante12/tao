# echo "setup ChargeTemplatePos v0 in /dybfs/users/xuhangkun/SimTAO/offline/tao_offline/Simulation/DetSim"

if test "${CMTROOT}" = ""; then
  CMTROOT=/cvmfs/juno.ihep.ac.cn/centos7_amd64_gcc830/Pre-Release/J20v2r0-branch/ExternalLibs/CMT/v1r26; export CMTROOT
fi
. ${CMTROOT}/mgr/setup.sh
cmtChargeTemplatePostempfile=`${CMTROOT}/mgr/cmt -quiet build temporary_name`
if test ! $? = 0 ; then cmtChargeTemplatePostempfile=/tmp/cmt.$$; fi
${CMTROOT}/mgr/cmt setup -sh -pack=ChargeTemplatePos -version=v0 -path=/dybfs/users/xuhangkun/SimTAO/offline/tao_offline/Simulation/DetSim  -no_cleanup $* >${cmtChargeTemplatePostempfile}
if test $? != 0 ; then
  echo >&2 "${CMTROOT}/mgr/cmt setup -sh -pack=ChargeTemplatePos -version=v0 -path=/dybfs/users/xuhangkun/SimTAO/offline/tao_offline/Simulation/DetSim  -no_cleanup $* >${cmtChargeTemplatePostempfile}"
  cmtsetupstatus=2
  /bin/rm -f ${cmtChargeTemplatePostempfile}
  unset cmtChargeTemplatePostempfile
  return $cmtsetupstatus
fi
cmtsetupstatus=0
. ${cmtChargeTemplatePostempfile}
if test $? != 0 ; then
  cmtsetupstatus=2
fi
/bin/rm -f ${cmtChargeTemplatePostempfile}
unset cmtChargeTemplatePostempfile
return $cmtsetupstatus

