// Do NOT change. Changes will be lost next time file is generated

#define R__DICTIONARY_FILENAME dItmpdIbdIjunodOihepdOacdOcndIel9_amd64_gcc11dIReleasedIJ25dO7dO1dItaoswdIbuilddIDataModeldICalibEventdIsrcdICdCalibHeaderDict
#define R__NO_DEPRECATION

/*******************************************************************/
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#define G__DICTIONARY
#include "ROOT/RConfig.hxx"
#include "TClass.h"
#include "TDictAttributeMap.h"
#include "TInterpreter.h"
#include "TROOT.h"
#include "TBuffer.h"
#include "TMemberInspector.h"
#include "TInterpreter.h"
#include "TVirtualMutex.h"
#include "TError.h"

#ifndef G__ROOT
#define G__ROOT
#endif

#include "RtypesImp.h"
#include "TIsAProxy.h"
#include "TFileMergeInfo.h"
#include <algorithm>
#include "TCollectionProxyInfo.h"
/*******************************************************************/

#include "TDataMember.h"

// Header files passed as explicit arguments
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/CalibEvent/Event/CdCalibHeader.h"

// Header files passed via #pragma extra_include

// The generated code does not explicitly qualify STL entities
namespace std {} using namespace std;

namespace ROOT {
   static void *new_TaocLcLCdCalibHeader(void *p = nullptr);
   static void *newArray_TaocLcLCdCalibHeader(Long_t size, void *p);
   static void delete_TaocLcLCdCalibHeader(void *p);
   static void deleteArray_TaocLcLCdCalibHeader(void *p);
   static void destruct_TaocLcLCdCalibHeader(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const ::Tao::CdCalibHeader*)
   {
      ::Tao::CdCalibHeader *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TInstrumentedIsAProxy< ::Tao::CdCalibHeader >(nullptr);
      static ::ROOT::TGenericClassInfo 
         instance("Tao::CdCalibHeader", ::Tao::CdCalibHeader::Class_Version(), "Event/CdCalibHeader.h", 10,
                  typeid(::Tao::CdCalibHeader), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &::Tao::CdCalibHeader::Dictionary, isa_proxy, 4,
                  sizeof(::Tao::CdCalibHeader) );
      instance.SetNew(&new_TaocLcLCdCalibHeader);
      instance.SetNewArray(&newArray_TaocLcLCdCalibHeader);
      instance.SetDelete(&delete_TaocLcLCdCalibHeader);
      instance.SetDeleteArray(&deleteArray_TaocLcLCdCalibHeader);
      instance.SetDestructor(&destruct_TaocLcLCdCalibHeader);
      return &instance;
   }
   TGenericClassInfo *GenerateInitInstance(const ::Tao::CdCalibHeader*)
   {
      return GenerateInitInstanceLocal(static_cast<::Tao::CdCalibHeader*>(nullptr));
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const ::Tao::CdCalibHeader*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));
} // end of namespace ROOT

namespace Tao {
//______________________________________________________________________________
atomic_TClass_ptr CdCalibHeader::fgIsA(nullptr);  // static to hold class pointer

//______________________________________________________________________________
const char *CdCalibHeader::Class_Name()
{
   return "Tao::CdCalibHeader";
}

//______________________________________________________________________________
const char *CdCalibHeader::ImplFileName()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::CdCalibHeader*)nullptr)->GetImplFileName();
}

//______________________________________________________________________________
int CdCalibHeader::ImplFileLine()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::CdCalibHeader*)nullptr)->GetImplFileLine();
}

//______________________________________________________________________________
TClass *CdCalibHeader::Dictionary()
{
   fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::CdCalibHeader*)nullptr)->GetClass();
   return fgIsA;
}

//______________________________________________________________________________
TClass *CdCalibHeader::Class()
{
   if (!fgIsA.load()) { R__LOCKGUARD(gInterpreterMutex); fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::CdCalibHeader*)nullptr)->GetClass(); }
   return fgIsA;
}

} // namespace Tao
namespace Tao {
//______________________________________________________________________________
void CdCalibHeader::Streamer(TBuffer &R__b)
{
   // Stream an object of class Tao::CdCalibHeader.

   if (R__b.IsReading()) {
      R__b.ReadClassBuffer(Tao::CdCalibHeader::Class(),this);
   } else {
      R__b.WriteClassBuffer(Tao::CdCalibHeader::Class(),this);
   }
}

} // namespace Tao
namespace ROOT {
   // Wrappers around operator new
   static void *new_TaocLcLCdCalibHeader(void *p) {
      return  p ? new(p) ::Tao::CdCalibHeader : new ::Tao::CdCalibHeader;
   }
   static void *newArray_TaocLcLCdCalibHeader(Long_t nElements, void *p) {
      return p ? new(p) ::Tao::CdCalibHeader[nElements] : new ::Tao::CdCalibHeader[nElements];
   }
   // Wrapper around operator delete
   static void delete_TaocLcLCdCalibHeader(void *p) {
      delete (static_cast<::Tao::CdCalibHeader*>(p));
   }
   static void deleteArray_TaocLcLCdCalibHeader(void *p) {
      delete [] (static_cast<::Tao::CdCalibHeader*>(p));
   }
   static void destruct_TaocLcLCdCalibHeader(void *p) {
      typedef ::Tao::CdCalibHeader current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class ::Tao::CdCalibHeader

namespace {
  void TriggerDictionaryInitialization_CdCalibHeaderDict_Impl() {
    static const char* headers[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/CalibEvent/Event/CdCalibHeader.h",
nullptr
    };
    static const char* includePaths[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Python/3.11.10/include/python3.11",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Boost/1.85.0",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/log4cpp/1.1.3/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/ROOT/6.30.08/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J24.2.0/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Geant4/10.04.p02.juno/include/geant4",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/HepMC/2.06.11/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/genie/3.04.02/include/GENIE",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/frontier/2.10.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-c/6.1.9/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-cpp/1.1.12/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libyaml/0.2.4/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime/core/session",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/nuwro/21.09.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/CalibEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/CalibEvent/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/CalibEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.4.0/ExternalLibs/ROOT/6.30.08/include/",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/CalibEvent/",
nullptr
    };
    static const char* fwdDeclCode = R"DICTFWDDCLS(
#line 1 "CdCalibHeaderDict dictionary forward declarations' payload"
#pragma clang diagnostic ignored "-Wkeyword-compat"
#pragma clang diagnostic ignored "-Wignored-attributes"
#pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
extern int __Cling_AutoLoading_Map;
namespace Tao{class __attribute__((annotate("$clingAutoload$/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/CalibEvent/Event/CdCalibHeader.h")))  CdCalibHeader;}
)DICTFWDDCLS";
    static const char* payloadCode = R"DICTPAYLOAD(
#line 1 "CdCalibHeaderDict dictionary payload"


#define _BACKWARD_BACKWARD_WARNING_H
// Inline headers
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/CalibEvent/Event/CdCalibHeader.h"

#undef  _BACKWARD_BACKWARD_WARNING_H
)DICTPAYLOAD";
    static const char* classesHeaders[] = {
"Tao::CdCalibHeader", payloadCode, "@",
nullptr
};
    static bool isInitialized = false;
    if (!isInitialized) {
      TROOT::RegisterModule("CdCalibHeaderDict",
        headers, includePaths, payloadCode, fwdDeclCode,
        TriggerDictionaryInitialization_CdCalibHeaderDict_Impl, {}, classesHeaders, /*hasCxxModule*/false);
      isInitialized = true;
    }
  }
  static struct DictInit {
    DictInit() {
      TriggerDictionaryInitialization_CdCalibHeaderDict_Impl();
    }
  } __TheDictionaryInitializer;
}
void TriggerDictionaryInitialization_CdCalibHeaderDict() {
  TriggerDictionaryInitialization_CdCalibHeaderDict_Impl();
}
